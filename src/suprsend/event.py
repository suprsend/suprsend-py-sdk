import json
import uuid
import time
from datetime import datetime, timezone
import requests
from typing import List, Dict

from .constants import (HEADER_DATE_FMT, BODY_MAX_APPARENT_SIZE_IN_BYTES, BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE)
from .signature import get_request_signature
from .utils import (get_apparent_body_size, validate_track_event_schema)


RESERVED_EVENT_NAMES = [
    "$identify",
    "$notification_delivered", "$notification_dismiss", "$notification_clicked",
    "$app_launched", "$user_login", "$user_logout",
]


class EventCollector:
    def __init__(self, config):
        self.config = config
        self.__url = self.__get_url()
        self.__headers = self.__common_headers()
        self.__supr_props = self.__super_properties()

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

    def __super_properties(self):
        return {
            "$ss_sdk_version": self.config.user_agent
        }

    def __check_event_prefix(self, event_name: str):
        if event_name not in RESERVED_EVENT_NAMES:
            prefix_3_chars = event_name[:3].lower()
            if prefix_3_chars.startswith("$") or prefix_3_chars == "ss_":
                raise ValueError("event_names starting with [$,ss_] are reserved")

    def __validate_event_name(self, event_name: str) -> str:
        if not isinstance(event_name, (str,)):
            return event_name
        event_name = event_name.strip()
        self.__check_event_prefix(event_name)
        return event_name

    def collect(self, distinct_id: str, event_name: str, properties: Dict) -> Dict:
        event_name = self.__validate_event_name(event_name)
        if not properties:
            properties = {}
        if not isinstance(properties, (dict,)):
            raise ValueError("properties must be a dictionary")
        properties = {**properties, **self.__supr_props}
        # -----
        event = {
            "$insert_id": str(uuid.uuid4()),
            "$time": int(time.time() * 1000),
            "event": event_name,
            "env": self.config.workspace_key,
            "distinct_id": distinct_id,
            "properties": properties
        }
        event = validate_track_event_schema(event)
        return self.send(event)

    def send(self, event) -> Dict:
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
