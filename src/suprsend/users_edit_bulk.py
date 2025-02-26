import copy
from datetime import datetime, timezone
import requests
from typing import Dict, Union

from .constants import (
    IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES,
    IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
    BODY_MAX_APPARENT_SIZE_IN_BYTES,
    MAX_IDENTITY_EVENTS_IN_BULK_API,
    HEADER_DATE_FMT,
)
from .exception import InputValueError
from .signature import get_request_signature
from .utils import invalid_record_json
from .bulk_response import BulkResponse
from .user_edit import UserEdit


class _BulkUsersEditChunk:
    _chunk_apparent_size_in_bytes = BODY_MAX_APPARENT_SIZE_IN_BYTES
    _max_records_in_chunk = MAX_IDENTITY_EVENTS_IN_BULK_API

    def __init__(self, config):
        self.config = config
        self.__chunk = []
        self.__url = "{}event/".format(self.config.base_url)
        #
        self.__running_size = 0
        self.__running_length = 0
        self.response = None

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.config.user_agent,
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
        }

    def __add_event_to_chunk(self, event, event_size):
        # First add size, then event to reduce effects of race condition
        self.__running_size += event_size
        self.__chunk.append(event)
        self.__running_length += 1

    def __check_limit_reached(self):
        if self.__running_length >= self._max_records_in_chunk or \
                self.__running_size >= self._chunk_apparent_size_in_bytes:
            return True
        else:
            return False

    def try_to_add_into_chunk(self, event: Dict, event_size: int) -> bool:
        """
        returns whether passed event was able to get added to this chunk or not,
        if true, event gets added to chunk
        :param event:
        :param event_size:
        :return:
        :raises: InputValueError
        """
        if not event:
            return True
        if self.__check_limit_reached():
            return False
        # ---
        if event_size > IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise InputValueError(f"Event too big - {event_size} Bytes, "
                                  f"must not cross {IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # if apparent_size of event crosses limit
        if self.__running_size + event_size > self._chunk_apparent_size_in_bytes:
            return False

        # Add Event to chunk
        self.__add_event_to_chunk(event, event_size)
        return True

    def trigger(self):
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(self.__url, "POST", self.__chunk, headers,
                                                 self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        try:
            resp = requests.post(self.__url, data=content_txt.encode('utf-8'), headers=headers)
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


class BulkUsersEdit:
    def __init__(self, config):
        self.config = config
        self.__users = []
        self.__pending_records = []
        # invalid_record json: {"record": event-json, "error": error_str, "code": 500}
        self.__invalid_records = []
        self.chunks = []
        self.response = BulkResponse()

    def __validate_users(self):
        for u in self.__users:
            try:
                # -- check if there is any error/warning, if so add it to warnings list of BulkResponse
                warnings_list = u.validate_body()
                if warnings_list:
                    self.response.warnings.extend(warnings_list)
                # ---
                pl = u.get_async_payload()
                pl_json, pl_size = u.validate_payload_size(pl)
                self.__pending_records.append((pl_json, pl_size))
            except Exception as ex:
                # invalid_record json: {"record": payload-json, "error": error_str, "code": 500}
                inv_rec = invalid_record_json(u.as_json_async(), ex)
                self.__invalid_records.append(inv_rec)

    def __chunkify(self, start_idx=0):
        curr_chunk = _BulkUsersEditChunk(self.config)
        self.chunks.append(curr_chunk)
        for rel_idx, rec in enumerate(self.__pending_records[start_idx:]):
            is_added = curr_chunk.try_to_add_into_chunk(rec[0], rec[1])
            if not is_added:
                # create chunks from remaining records
                self.__chunkify(start_idx=(start_idx + rel_idx))
                # Don't forget to break. As current loop must not continue further
                break

    def append(self, *users):
        if not users:
            return
        for u in users:
            if u and isinstance(u, UserEdit):
                u_copy = copy.deepcopy(u)
                self.__users.append(u_copy)

    def save(self):
        self.__validate_users()
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
