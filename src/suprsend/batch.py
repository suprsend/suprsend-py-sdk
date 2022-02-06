from datetime import datetime, timezone
import requests
import json
import copy

from .constants import (
    BODY_MAX_APPARENT_SIZE_IN_BYTES,
    BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
    MAX_RECORDS_IN_BATCH,
    ALLOW_ATTACHMENTS_IN_BATCH,
    HEADER_DATE_FMT,
)
from .signature import get_request_signature
from .utils import (get_apparent_body_size, validate_workflow_body_schema, )


class BatchFactory:

    def __init__(self, config):
        self.config = config

    def new(self):
        """
        USAGE:
        supr_client = Suprsend("__workspace_key__", "__workspace_secret__")
        batch_ins = supr_client.batch.new()

        # append one by one
        for i in range(0, 10):
            wbody = {...} # prepare workflow body
            batch_ins.append(wbody)

        # append many in one call
        all_wbody = [{...}, {...}, ...] # multiple workflow bodies
        batch_ins.append(*all_wbody)

        # call trigger
        response = batch_ins.trigger()

        :return:
        """
        return BatchWorkflowTrigger(self.config)


class BatchResponse:
    def __init__(self):
        self.status = None
        self.failed_records = []
        self.total = 0
        self.success = 0
        self.failure = 0

    def __str__(self):
        return f"BatchResponse<status:{self.status}| success: {self.success} | failure: {self.failure} | " \
               f"total: {self.total}>"

    def merge_chunk_response(self, ch_resp):
        if not ch_resp:
            return
        # possible status: success/partial/fail
        if self.status is None:
            self.status = ch_resp["status"]
        else:
            if self.status == "success":
                if ch_resp["status"] == "fail":
                    self.status = "partial"
            elif self.status == "fail":
                if ch_resp["status"] == "success":
                    self.status = "partial"
        self.total += ch_resp.get("total", 0)
        self.success += ch_resp.get("success", 0)
        self.failure += ch_resp.get("failure", 0)
        failed_recs = ch_resp.get("failed_records", [])
        self.failed_records.extend(failed_recs)


class _BatchChunk:
    _chunk_apparent_size_in_bytes = BODY_MAX_APPARENT_SIZE_IN_BYTES
    _chunk_apparent_size_in_bytes_readable = BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE
    _max_records_in_chunk = MAX_RECORDS_IN_BATCH

    def __init__(self, config):
        self.__config = config
        self.__chunk = []
        self.__url = self.__get_url()
        #
        self.__running_size = 0
        self.__running_length = 0
        self.response = None

    def __get_url(self):
        url_template = "{}{}/trigger/"
        if self.__config.include_signature_param:
            if self.__config.auth_enabled:
                url_template = url_template + "?verify=true"
            else:
                url_template = url_template + "?verify=false"
        url_formatted = url_template.format(self.__config.base_url, self.__config.workspace_key)
        return url_formatted

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
            "User-Agent": self.__config.user_agent,
        }

    def __add_body_to_chunk(self, body, body_size):
        # First add size, then body to reduce effects of race condition
        self.__running_size += body_size
        self.__chunk.append(body)
        self.__running_length += 1

    def __check_limit_reached(self):
        if self.__running_length >= self._max_records_in_chunk or \
                self.__running_size >= self._chunk_apparent_size_in_bytes:
            return True
        else:
            return False

    def try_to_add_into_chunk(self, body) -> bool:
        """
        returns whether passed body was able to get added to this chunk or not,
        if true, body gets added to chunk
        :param body:
        :return:
        :raises: ValueError
        """
        if not body:
            return True
        if self.__check_limit_reached():
            return False
        # ---
        apparent_size = get_apparent_body_size(body)
        # --
        if apparent_size > self._chunk_apparent_size_in_bytes:
            raise ValueError(f"workflow body (discounting attachment if any) too big - {apparent_size} Bytes, "
                             f"must not cross {self._chunk_apparent_size_in_bytes_readable}")
        # if apparent_size of body crosses limit
        if self.__running_size + apparent_size > self._chunk_apparent_size_in_bytes:
            return False

        if not ALLOW_ATTACHMENTS_IN_BATCH:
            body["data"].pop("$attachments", None)

        # Add workflow to chunk
        self.__add_body_to_chunk(body, apparent_size)
        return True

    def trigger(self):
        headers = self.__get_headers()
        # Based on whether signature is required or not, add Authorization header
        if self.__config.auth_enabled:
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(self.__url, 'POST', self.__chunk, headers,
                                                     self.__config.workspace_secret)
            headers["Authorization"] = "{}:{}".format(self.__config.workspace_key, sig)
        else:
            content_txt = json.dumps(self.__chunk, ensure_ascii=False)
        # -----
        try:
            resp = requests.post(self.__url,
                                 data=content_txt.encode('utf-8'),
                                 headers=headers)
        except Exception as ex:
            error_str = ex.__str__()
            self.response = {
                # status: success/fail
                "status": "fail",
                "status_code": 500,
                "total": len(self.__chunk),
                "success": 0,
                "failure": len(self.__chunk),
                "failed_records": [{"record": c, "error": error_str, "code": 500} for c in self.__chunk]
            }
        else:
            # TODO: handle 500/503 errors
            ok_response = resp.status_code // 100 == 2
            if ok_response:
                self.response = {
                    # status: success/fail
                    "status": "success",
                    "status_code": resp.status_code,
                    "total": len(self.__chunk),
                    "success": len(self.__chunk),
                    "failure": 0,
                    "failed_records": []
                }
            else:
                error_str = resp.text
                self.response = {
                    # status: success/fail
                    "status": "fail",
                    "status_code": resp.status_code,
                    "total": len(self.__chunk),
                    "success": 0,
                    "failure": len(self.__chunk),
                    "failed_records": [{"record": c, "error": error_str, "code": resp.status_code}
                                       for c in self.__chunk]
                }


class BatchWorkflowTrigger:
    def __init__(self, config):
        self.__config = config
        self.__pending_records = []
        self.chunks = []
        self.response = BatchResponse()

    def __validate_body(self):
        if not self.__pending_records:
            raise ValueError("body is empty in batch request")
        for b in self.__pending_records:
            validate_workflow_body_schema(b)

    def __chunkify(self, start_idx=0):
        curr_chunk = _BatchChunk(self.__config)
        self.chunks.append(curr_chunk)
        for rel_idx, body in enumerate(self.__pending_records[start_idx:]):
            is_added = curr_chunk.try_to_add_into_chunk(body)
            if not is_added:
                # create chunks from remaining records
                self.__chunkify(start_idx=(start_idx + rel_idx))
                # Don't forget to break. As current loop must not continue further
                break

    def append(self, *body):
        if not body:
            raise ValueError("body list empty. must pass one or more valid workflow body")
        for bd in body:
            if not bd:
                raise ValueError("body element is empty. must be a valid workflow body")
            if not isinstance(bd, (dict,)):
                raise ValueError("body element must be a dict")
            bd_copy = copy.deepcopy(bd)
            self.__pending_records.append(bd_copy)

    def trigger(self):
        self.__validate_body()
        self.__chunkify()
        for c_idx, ch in enumerate(self.chunks):
            if self.__config.req_log_level > 0:
                print(f"DEBUG: triggering api call for chunk: {c_idx}")
            # do api call
            ch.trigger()
            # merge response
            self.response.merge_chunk_response(ch.response)
        # -----
        return self.response
