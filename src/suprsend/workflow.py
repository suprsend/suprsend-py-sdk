from datetime import datetime, timezone
import requests
import json
from typing import Dict

from .constants import (HEADER_DATE_FMT, BODY_MAX_APPARENT_SIZE_IN_BYTES, BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE)
from .utils import (get_apparent_body_size, validate_workflow_body_schema)
from .signature import get_request_signature


class WorkflowTrigger:
    def __init__(self, config, data: Dict):
        self.config = config
        self.data = data
        self.url = self.__get_url()

    def __get_url(self):
        url_template = "{}{}/trigger/"
        if self.config.include_signature_param:
            if self.config.auth_enabled:
                url_template = url_template + "?verify=true"
            else:
                url_template = url_template + "?verify=false"
        url_formatted = url_template.format(self.config.base_url, self.config.workspace_key)
        # ---
        # self.url = quote_plus(url_formatted)
        return url_formatted

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
            "User-Agent": self.config.user_agent,
        }

    def execute_workflow(self):
        headers = self.__get_headers()
        # Based on whether signature is required or not, add Authorization header
        if self.config.auth_enabled:
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(self.url, 'POST', self.data, headers, self.config.workspace_secret)
            headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        else:
            content_txt = json.dumps(self.data, ensure_ascii=False)
        # -----
        try:
            resp = requests.post(self.url,
                                 data=content_txt.encode('utf-8'),
                                 headers=headers)
        except Exception as ex:
            error_str = ex.__str__()
            return {
                "success": False,
                "status": 500,
                "message": error_str,
            }
        else:
            success = resp.status_code // 100 == 2
            return {
                "success": success,
                "status": resp.status_code,
                "message": resp.text,
            }

    def validate_data(self):
        self.data = validate_workflow_body_schema(self.data)
        # ---- Check body size
        apparent_size = get_apparent_body_size(self.data)
        if apparent_size > BODY_MAX_APPARENT_SIZE_IN_BYTES:
            raise ValueError(f"workflow body (discounting attachment if any) too big - {apparent_size} Bytes, "
                             f"must not cross {BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return self.data
