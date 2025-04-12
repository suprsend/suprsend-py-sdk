from .constants import (
    BODY_MAX_APPARENT_SIZE_IN_BYTES, BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
)
from .exception import InputValueError
from .attachment import get_attachment_json
from .utils import (get_apparent_workflow_body_size, validate_workflow_trigger_body_schema)


class WorkflowTriggerRequest:
    def __init__(self, body, idempotency_key: str = None, tenant_id: str = None, cancellation_key: str = None):
        if not isinstance(body, (dict,)):
            raise InputValueError("WorkflowTriggerRequest body must be a json/dictionary")
        self.body = body
        self.idempotency_key = idempotency_key
        self.tenant_id = tenant_id
        self.cancellation_key = cancellation_key

    def add_attachment(self, file_path: str, file_name: str = None, ignore_if_error: bool = False):
        if self.body.get("data") is None:
            self.body["data"] = {}
        # if body["data"] is not a dict, not raising error while adding attachment.
        if not isinstance(self.body["data"], (dict,)):
            print("WARNING: attachment cannot be added. please make sure body['data'] is a dictionary. "
                  "WorkflowTriggerRequest" + str(self.as_json()))
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
        if self.tenant_id:
            self.body["tenant_id"] = self.tenant_id
        if self.cancellation_key:
            self.body["cancellation_key"] = self.cancellation_key
        # --
        self.body = validate_workflow_trigger_body_schema(self.body)
        # ---- Check body size
        apparent_size = get_apparent_workflow_body_size(self.body, is_part_of_bulk)
        if apparent_size > BODY_MAX_APPARENT_SIZE_IN_BYTES:
            raise InputValueError(f"workflow body too big - {apparent_size} Bytes, "
                                  f"must not cross {BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return self.body, apparent_size

    def as_json(self):
        body_dict = {**self.body}
        if self.idempotency_key:
            body_dict["$idempotency_key"] = self.idempotency_key
        if self.tenant_id:
            body_dict["tenant_id"] = self.tenant_id
        if self.cancellation_key:
            self.body["cancellation_key"] = self.cancellation_key
        # -----
        return body_dict
