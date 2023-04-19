from datetime import datetime, timezone
import requests
from typing import Dict

from .constants import (
    HEADER_DATE_FMT,
    SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES, SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
)
from .exception import InputValueError
from .utils import (get_apparent_workflow_body_size, validate_workflow_body_schema)
from .signature import get_request_signature
from .attachment import get_attachment_json


class Workflow:
    def __init__(self, body, idempotency_key: str = None, brand_id: str = None):
        if not isinstance(body, (dict,)):
            raise InputValueError("workflow body must be a json/dictionary")
        self.body = body
        self.idempotency_key = idempotency_key
        self.brand_id = brand_id

    def add_attachment(self, file_path: str, file_name: str = None, ignore_if_error: bool = False):
        if self.body.get("data") is None:
            self.body["data"] = {}
        # if body["data"] is not a dict, not raising error while adding attachment.
        if not isinstance(self.body["data"], (dict,)):
            print("WARNING: attachment cannot be added. please make sure body['data'] is a dictionary. Workflow" +
                  str(self.as_json()))
            return
        # ---
        attachment = get_attachment_json(file_path, file_name, ignore_if_error)
        if not attachment:
            return
        # --- add the attachment to body->data->$attachments
        if self.body["data"].get("$attachments") is None:
            self.body["data"]["$attachments"] = []
        # -----
        self.body["data"]["$attachments"].append(attachment)

    def get_final_json(self, config, is_part_of_bulk: bool = False):
        # add idempotency key in body if present
        if self.idempotency_key:
            self.body["$idempotency_key"] = self.idempotency_key
        if self.brand_id:
            self.body["brand_id"] = self.brand_id
        # --
        self.body = validate_workflow_body_schema(self.body)
        # ---- Check body size
        apparent_size = get_apparent_workflow_body_size(self.body, is_part_of_bulk)
        if apparent_size > SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise InputValueError(f"workflow body too big - {apparent_size} Bytes, "
                                  f"must not cross {SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return self.body, apparent_size

    def as_json(self):
        body_dict = {**self.body}
        if self.idempotency_key:
            body_dict["$idempotency_key"] = self.idempotency_key
        if self.brand_id:
            body_dict["brand_id"] = self.brand_id
        # -----
        return body_dict


class _WorkflowTrigger:
    def __init__(self, config):
        self.config = config
        self.url = self.__get_url()

    def __get_url(self):
        url_formatted = "{}{}/trigger/".format(self.config.base_url, self.config.workspace_key)
        return url_formatted

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
            "User-Agent": self.config.user_agent,
        }

    def trigger(self, workflow: Workflow) -> Dict:
        workflow_body, body_size = workflow.get_final_json(self.config, is_part_of_bulk=False)
        return self.send(workflow_body)

    def send(self, workflow_body: Dict) -> Dict:
        try:
            headers = self.__get_headers()
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(self.url, 'POST', workflow_body,
                                                     headers, self.config.workspace_secret)
            headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
            # -----
            resp = requests.post(self.url,
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
