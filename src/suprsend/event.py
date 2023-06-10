from datetime import datetime, timezone
import requests
import time
from typing import List, Dict
import uuid

from .constants import (
    HEADER_DATE_FMT,
    SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES, SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
)
from .exception import InputValueError
from .attachment import get_attachment_json
from .signature import get_request_signature
from .utils import (validate_track_event_schema, get_apparent_event_size, )


RESERVED_EVENT_NAMES = [
    "$identify",
    "$notification_delivered", "$notification_dismiss", "$notification_clicked",
    "$app_launched", "$user_login", "$user_logout",
]


class Event:
    def __init__(self, distinct_id: str, event_name: str, properties: Dict = None,
                 idempotency_key: str = None, brand_id: str = None):
        self.distinct_id = distinct_id
        self.event_name = event_name
        self.properties = properties
        self.idempotency_key = idempotency_key
        self.brand_id = brand_id
        # default values
        if self.properties is None:
            self.properties = {}

    def __validate_distinct_id(self):
        if not isinstance(self.distinct_id, (str,)):
            raise InputValueError("distinct_id must be a string. an Id which uniquely identify a user in your app")
        distinct_id = self.distinct_id.strip()
        if not distinct_id:
            raise InputValueError("distinct_id missing")
        self.distinct_id = distinct_id

    def __validate_properties(self):
        if not isinstance(self.properties, (dict,)):
            raise InputValueError("properties must be a dictionary")

    def __check_event_prefix(self, event_name: str):
        if event_name not in RESERVED_EVENT_NAMES:
            prefix_3_chars = event_name[:3].lower()
            if prefix_3_chars.startswith("$") or prefix_3_chars == "ss_":
                raise InputValueError("event_names starting with [$,ss_] are reserved by SuprSend")

    def __validate_event_name(self):
        if not isinstance(self.event_name, (str,)):
            raise InputValueError("event_name must be a string")
        event_name = self.event_name.strip()
        if not event_name:
            raise InputValueError("event_name missing")
        self.__check_event_prefix(event_name)
        self.event_name = event_name

    def add_attachment(self, file_path: str, file_name: str = None, ignore_if_error: bool = False):
        # if properties is not a dict, not raising error while adding attachment.
        if not isinstance(self.properties, (dict,)):
            print("WARNING: attachment cannot be added. please make sure properties is a dictionary. Event" +
                  str(self.as_json()))
            return
        # ---
        attachment = get_attachment_json(file_path, file_name, ignore_if_error)
        if not attachment:
            return
        # --- add the attachment to properties->$attachments
        if self.properties.get("$attachments") is None:
            self.properties["$attachments"] = []
        # -----
        self.properties["$attachments"].append(attachment)

    def get_final_json(self, config, is_part_of_bulk: bool = False):
        # --- validate
        self.__validate_distinct_id()
        self.__validate_event_name()
        self.__validate_properties()
        # ---
        super_props = {"$ss_sdk_version": config.user_agent}
        event_dict = {
            "$insert_id": str(uuid.uuid4()),
            "$time": int(time.time() * 1000),
            "event": self.event_name,
            "env": config.workspace_key,
            "distinct_id": self.distinct_id,
            "properties": {**self.properties, **super_props}
        }
        if self.idempotency_key:
            event_dict["$idempotency_key"] = self.idempotency_key
        if self.brand_id:
            event_dict["brand_id"] = self.brand_id
        # ---
        event_dict = validate_track_event_schema(event_dict)
        # ---- Check size
        apparent_size = get_apparent_event_size(event_dict, is_part_of_bulk)
        if apparent_size > SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise InputValueError(f"Event size too big - {apparent_size} Bytes, "
                                  f"must not cross {SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return event_dict, apparent_size

    def as_json(self):
        event_dict = {
            "event": self.event_name,
            "distinct_id": self.distinct_id,
            "properties": self.properties,
        }
        if self.idempotency_key:
            event_dict["$idempotency_key"] = self.idempotency_key
        if self.brand_id:
            event_dict["brand_id"] = self.brand_id
        # -----
        return event_dict


class EventCollector:
    def __init__(self, config):
        self.config = config
        self.__url = self.__get_url()
        self.__headers = self.__common_headers()

    def __get_url(self):
        url_formatted = "{}event/".format(self.config.base_url)
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
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(self.__url, 'POST', event, headers,
                                                     self.config.workspace_secret)
            headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
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
