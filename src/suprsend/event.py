import json
import uuid
import time
from datetime import datetime, timezone
import requests
from typing import List, Dict

from .constants import (HEADER_DATE_FMT, BODY_MAX_APPARENT_SIZE_IN_BYTES, BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE)
from .attachment import get_attachment_json_for_file
from .signature import get_request_signature
from .utils import (validate_track_event_schema, get_apparent_event_size, )


RESERVED_EVENT_NAMES = [
    "$identify",
    "$notification_delivered", "$notification_dismiss", "$notification_clicked",
    "$app_launched", "$user_login", "$user_logout",
]


class Event:
    def __init__(self, distinct_id: str, event_name: str, properties: Dict = None):
        self.distinct_id = distinct_id
        self.event_name = event_name
        self.properties = properties
        # --- validate
        self.__validate_distinct_id()
        self.__validate_event_name()
        self.__validate_properties()

    def __validate_distinct_id(self):
        if not isinstance(self.distinct_id, (str,)):
            raise ValueError("distinct_id must be a string. an Id which uniquely identify a user in your app")
        distinct_id = self.distinct_id.strip()
        if not distinct_id:
            raise ValueError("distinct_id missing")
        self.distinct_id = distinct_id

    def __validate_properties(self):
        if self.properties is None:
            self.properties = {}
        if not isinstance(self.properties, (dict,)):
            raise ValueError("properties must be a dictionary")

    def __check_event_prefix(self, event_name: str):
        if event_name not in RESERVED_EVENT_NAMES:
            prefix_3_chars = event_name[:3].lower()
            if prefix_3_chars.startswith("$") or prefix_3_chars == "ss_":
                raise ValueError("event_names starting with [$,ss_] are reserved by SuprSend")

    def __validate_event_name(self):
        if not isinstance(self.event_name, (str,)):
            raise ValueError("event_name must be a string")
        event_name = self.event_name.strip()
        if not event_name:
            raise ValueError("event_name missing")
        self.__check_event_prefix(event_name)
        self.event_name = event_name

    def add_attachment(self, file_path: str):
        attachment = get_attachment_json_for_file(file_path)
        # --- add the attachment to body->data->$attachments
        if self.properties.get("$attachments") is None:
            self.properties["$attachments"] = []
        # -----
        self.properties["$attachments"].append(attachment)

    def get_final_json(self, config, is_part_of_bulk: bool = False):
        super_props = {"$ss_sdk_version": config.user_agent}
        event_dict = {
            "$insert_id": str(uuid.uuid4()),
            "$time": int(time.time() * 1000),
            "event": self.event_name,
            "env": config.workspace_key,
            "distinct_id": self.distinct_id,
            "properties": {**self.properties, **super_props}
        }
        event_dict = validate_track_event_schema(event_dict)
        # ---- Check size
        apparent_size = get_apparent_event_size(event_dict, is_part_of_bulk)
        if apparent_size > BODY_MAX_APPARENT_SIZE_IN_BYTES:
            raise ValueError(f"Event properties too big - {apparent_size} Bytes, "
                             f"must not cross {BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return event_dict, apparent_size


class EventCollector:
    def __init__(self, config):
        self.config = config
        self.__url = self.__get_url()
        self.__headers = self.__common_headers()

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

    def collect(self, event: Event) -> Dict:
        event_dict, event_size = event.get_final_json(self.config, is_part_of_bulk=False)
        return self.send(event_dict)

    def send(self, event: Dict) -> Dict:
        try:
            headers = {**self.__headers, **self.__dynamic_headers()}
            # Based on whether signature is required or not, add Authorization header
            if self.config.auth_enabled:
                # Signature and Authorization-header
                content_txt, sig = get_request_signature(self.__url, 'POST', event, headers,
                                                         self.config.workspace_secret)
                headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
            else:
                content_txt = json.dumps(event, ensure_ascii=False)
            # -----
            resp = requests.post(self.__url,
                                 data=content_txt.encode('utf-8'),
                                 headers=headers)
        except Exception as ex:
            error_str = ex.__str__()
            return {
                "success": False,
                "status": "fail",
                "status_code": 500,
                "message": error_str,
            }
        else:
            ok_response = resp.status_code // 100 == 2
            if ok_response:
                return {
                    "success": True,
                    "status": "success",
                    "status_code": resp.status_code,
                    "message": resp.text,
                }
            else:
                return {
                    "success": False,
                    "status": "fail",
                    "status_code": resp.status_code,
                    "message": resp.text,
                }
