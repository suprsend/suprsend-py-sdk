from datetime import datetime, timezone
import requests
import json
import copy
from typing import List, Dict

from .constants import (
    SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES,
    SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
    BODY_MAX_APPARENT_SIZE_IN_BYTES,
    BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
    MAX_EVENTS_IN_BULK_API,
    ALLOW_ATTACHMENTS_IN_BULK_API,
    HEADER_DATE_FMT,
)
from .signature import get_request_signature
from .bulk_response import BulkResponse
from .event import Event


class BulkEventsFactory:

    def __init__(self, config):
        self.config = config

    def new_instance(self):
        """
        USAGE:
        supr_client = Suprsend("__workspace_key__", "__workspace_secret__")
        bulk_ins = supr_client.bulk_events.new_instance()

        # append one by one
        for i in range(0, 10):
            event = Event('distinct_id', 'event_name', {}) # create event instance
            bulk_ins.append(event)

        # append many in one call
        all_events = [Event(..), Event(..), ...] # multiple events
        bulk_ins.append(*all_events)

        # call trigger
        response = bulk_ins.trigger()

        :return:
        """
        return BulkEvents(self.config)


class _BulkEventsChunk:
    _chunk_apparent_size_in_bytes = BODY_MAX_APPARENT_SIZE_IN_BYTES
    _chunk_apparent_size_in_bytes_readable = BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE
    _max_records_in_chunk = MAX_EVENTS_IN_BULK_API

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
        url_template = "{}event/"
        if self.config.include_signature_param:
            if self.config.auth_enabled:
                url_template = url_template + "?verify=true"
            else:
                url_template = url_template + "?verify=false"
        url_formatted = url_template.format(self.config.base_url)
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
        :raises: ValueError
        """
        if not event:
            return True
        if self.__check_limit_reached():
            return False
        # ---
        if event_size > SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise ValueError(f"Event properties too big - {event_size} Bytes, "
                             f"must not cross {SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # if apparent_size of event crosses limit
        if self.__running_size + event_size > self._chunk_apparent_size_in_bytes:
            return False

        if not ALLOW_ATTACHMENTS_IN_BULK_API:
            event["properties"].pop("$attachments", None)

        # Add Event to chunk
        self.__add_event_to_chunk(event, event_size)
        return True

    def trigger(self):
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Based on whether signature is required or not, add Authorization header
        if self.config.auth_enabled:
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(self.__url, 'POST', self.__chunk, headers,
                                                     self.config.workspace_secret)
            headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
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


class BulkEvents:
    def __init__(self, config):
        self.config = config
        self.__events = []
        self.__pending_records = []
        self.chunks = []
        self.response = BulkResponse()

    def __validate_events(self):
        if not self.__events:
            raise ValueError("events list is empty in bulk request")
        for ev in self.__events:
            ev_json, body_size = ev.get_final_json(self.config, is_part_of_bulk=True)
            self.__pending_records.append((ev_json, body_size))

    def __chunkify(self, start_idx=0):
        curr_chunk = _BulkEventsChunk(self.config)
        self.chunks.append(curr_chunk)
        for rel_idx, rec in enumerate(self.__pending_records[start_idx:]):
            is_added = curr_chunk.try_to_add_into_chunk(rec[0], rec[1])
            if not is_added:
                # create chunks from remaining records
                self.__chunkify(start_idx=(start_idx + rel_idx))
                # Don't forget to break. As current loop must not continue further
                break

    def append(self, *events):
        if not events:
            raise ValueError("events list empty. must pass one or more events")
        for ev in events:
            if not ev:
                raise ValueError("null/empty element found in bulk instance")
            if not isinstance(ev, Event):
                raise ValueError("element must be an instance of suprsend.Event")
            ev_copy = copy.deepcopy(ev)
            self.__events.append(ev_copy)

    def trigger(self):
        self.__validate_events()
        self.__chunkify()
        for c_idx, ch in enumerate(self.chunks):
            if self.config.req_log_level > 0:
                print(f"DEBUG: triggering api call for chunk: {c_idx}")
            # do api call
            ch.trigger()
            # merge response
            self.response.merge_chunk_response(ch.response)
        # -----
        return self.response
