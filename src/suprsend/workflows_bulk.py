from datetime import datetime, timezone
import requests
import copy
from typing import List, Dict

from .constants import (
    SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES,
    SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
    BODY_MAX_APPARENT_SIZE_IN_BYTES,
    BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
    MAX_WORKFLOWS_IN_BULK_API,
    ALLOW_ATTACHMENTS_IN_BULK_API,
    HEADER_DATE_FMT,
)
from .exception import InputValueError
from .signature import get_request_signature
from .utils import invalid_record_json
from .bulk_response import BulkResponse
from .workflow import Workflow


class BulkWorkflowsFactory:

    def __init__(self, config):
        self.config = config

    def new_instance(self):
        """
        USAGE:
        supr_client = Suprsend("__workspace_key__", "__workspace_secret__")
        bulk_ins = supr_client.bulk_workflows.new_instance()

        # append one by one
        for i in range(0, 10):
            w = Workflow(body) # Workflow instance
            bulk_ins.append(w)

        # append many in one call
        all_workflows = [W1, W2, ...] # multiple workflows
        bulk_ins.append(*all_workflows)

        # call trigger
        response = bulk_ins.trigger()

        :return:
        """
        return BulkWorkflows(self.config)


class _BulkWorkflowsChunk:
    _chunk_apparent_size_in_bytes = BODY_MAX_APPARENT_SIZE_IN_BYTES
    _chunk_apparent_size_in_bytes_readable = BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE
    _max_records_in_chunk = MAX_WORKFLOWS_IN_BULK_API

    def __init__(self, config):
        self.config = config
        self.__chunk = []
        self.__url = self.__get_url()
        self.__headers = self.__common_headers()
        #
        self.__running_size = 0
        self.__running_length = 0
        self.response = None

    def __get_url(self):
        url_formatted = "{}{}/trigger/".format(self.config.base_url, self.config.workspace_key)
        return url_formatted

    def __common_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.config.user_agent,
        }

    def __dynamic_headers(self):
        return {
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
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

    def try_to_add_into_chunk(self, body: Dict, body_size: int) -> bool:
        """
        returns whether passed body was able to get added to this chunk or not,
        if true, body gets added to chunk
        :param body:
        :param body_size:
        :return:
        :raises: InputValueError
        """
        if not body:
            return True
        if self.__check_limit_reached():
            return False
        # ---
        if body_size > SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise InputValueError(f"workflow body too big - {body_size} Bytes, "
                                  f"must not cross {SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # if apparent_size of body crosses limit
        if self.__running_size + body_size > self._chunk_apparent_size_in_bytes:
            return False

        if not ALLOW_ATTACHMENTS_IN_BULK_API:
            body["data"].pop("$attachments", None)

        # Add workflow to chunk
        self.__add_body_to_chunk(body, body_size)
        return True

    def trigger(self):
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(self.__url, 'POST', self.__chunk, headers,
                                                 self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        try:
            resp = requests.post(self.__url,
                                 data=content_txt.encode('utf-8'),
                                 headers=headers)
        except Exception as ex:
            error_str = ex.__str__()
            self.response = {
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
                    "status": "fail",
                    "status_code": resp.status_code,
                    "total": len(self.__chunk),
                    "success": 0,
                    "failure": len(self.__chunk),
                    "failed_records": [{"record": c, "error": error_str, "code": resp.status_code}
                                       for c in self.__chunk]
                }


class BulkWorkflows:
    def __init__(self, config):
        self.config = config
        self.__workflows = []
        self.__pending_records = []
        self.chunks = []
        self.response = BulkResponse()
        # invalid_record json: {"record": workflow-json, "error": error_str, "code": 500}
        self.__invalid_records = []

    def __validate_workflows(self):
        for wf in self.__workflows:
            try:
                wf_body, body_size = wf.get_final_json(self.config, is_part_of_bulk=True)
                self.__pending_records.append((wf_body, body_size))
            except Exception as ex:
                inv_rec = invalid_record_json(wf.as_json(), ex)
                self.__invalid_records.append(inv_rec)

    def __chunkify(self, start_idx=0):
        curr_chunk = _BulkWorkflowsChunk(self.config)
        self.chunks.append(curr_chunk)
        for rel_idx, rec in enumerate(self.__pending_records[start_idx:]):
            is_added = curr_chunk.try_to_add_into_chunk(rec[0], rec[1])
            if not is_added:
                # create chunks from remaining records
                self.__chunkify(start_idx=(start_idx + rel_idx))
                # Don't forget to break. As current loop must not continue further
                break

    def append(self, *workflows):
        if not workflows:
            return
        for wf in workflows:
            if wf and isinstance(wf, Workflow):
                wf_copy = copy.deepcopy(wf)
                self.__workflows.append(wf_copy)

    def trigger(self):
        self.__validate_workflows()
        # --------
        if len(self.__invalid_records) > 0:
            ch_response = BulkResponse.invalid_records_chunk_response(self.__invalid_records)
            self.response.merge_chunk_response(ch_response)
        # --------
        if len(self.__pending_records):
            self.__chunkify()
            for c_idx, ch in enumerate(self.chunks):
                if self.config.req_log_level > 0:
                    print(f"DEBUG: triggering api call for chunk: {c_idx}")
                # do api call
                ch.trigger()
                # merge response
                self.response.merge_chunk_response(ch.response)
        else:
            # if no records. i.e. len(invalid_records) and len(pending_records) both are 0
            # then add empty success response
            if len(self.__invalid_records) == 0:
                self.response.merge_chunk_response(BulkResponse.empty_chunk_success_response())
        # -----
        return self.response
