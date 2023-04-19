from typing import Dict
import copy
import json
import jsonschema
import traceback

from .constants import (
    WORKFLOW_RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES,
    ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES,
    ATTACHMENT_UPLOAD_ENABLED, ALLOW_ATTACHMENTS_IN_BULK_API,
)
from .exception import SuprsendValidationError, InputValueError
from .request_schema import _get_schema_validator


def get_apparent_workflow_body_size(body: Dict, is_part_of_bulk: bool) -> int:
    # ---
    extra_bytes = WORKFLOW_RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES
    apparent_body = body
    # ---
    if body.get("data") and body["data"].get("$attachments"):
        num_attachments = len(body["data"]["$attachments"])
        if is_part_of_bulk:
            if ALLOW_ATTACHMENTS_IN_BULK_API:
                # if attachment is allowed in bulk api, then calculate size based on whether auto Upload is enabled
                if ATTACHMENT_UPLOAD_ENABLED:
                    # If auto upload enabled, To calculate size, replace attachment size with equivalent url size
                    extra_bytes += num_attachments * ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES
                    # -- remove attachments->data key to calculate data size
                    apparent_body = copy.deepcopy(body)
                    for attach_data in apparent_body["data"]["$attachments"]:
                        del attach_data["data"]
                    # ----
                else:
                    # if auto upload is not enabled, attachment data will be passed as it is.
                    pass
            else:
                # If attachment not allowed, then remove data->$attachments before calculating size
                apparent_body = copy.deepcopy(body)
                apparent_body["data"].pop("$attachments", None)
        else:
            if ATTACHMENT_UPLOAD_ENABLED:
                # if auto upload enabled, to calculate size, replace attachment size with equivalent url size
                extra_bytes += num_attachments * ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES
                # -- remove attachments->data key to calculate data size
                apparent_body = copy.deepcopy(body)
                for attach_data in apparent_body["data"]["$attachments"]:
                    del attach_data["data"]
                # ----
            else:
                # if auto upload is not enabled, attachment data will be passed as it is.
                pass

    # ---
    body_size = len(json.dumps(apparent_body, ensure_ascii=False).encode('utf-8'))
    apparent_body_size = body_size + extra_bytes
    # --
    return apparent_body_size


def get_apparent_event_size(event: Dict, is_part_of_bulk: bool) -> int:
    # ---
    extra_bytes = 0
    apparent_body = event
    # ---
    if event.get("properties") and event["properties"].get("$attachments"):
        num_attachments = len(event["properties"]["$attachments"])
        if is_part_of_bulk:
            if ALLOW_ATTACHMENTS_IN_BULK_API:
                # if attachment is allowed in bulk api, then calculate size based on whether auto Upload is enabled
                if ATTACHMENT_UPLOAD_ENABLED:
                    # If auto upload enabled, To calculate size, replace attachment size with equivalent url size
                    extra_bytes += num_attachments * ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES
                    # -- remove attachments->data key to calculate data size
                    apparent_body = copy.deepcopy(event)
                    for attach_data in apparent_body["properties"]["$attachments"]:
                        del attach_data["data"]
                    # ----
                else:
                    # if auto upload is not enabled, attachment data will be passed as it is.
                    pass
            else:
                # If attachment not allowed, then remove data->$attachments before calculating size
                apparent_body = copy.deepcopy(event)
                apparent_body["properties"].pop("$attachments", None)
        else:
            if ATTACHMENT_UPLOAD_ENABLED:
                # if auto upload enabled, to calculate size, replace attachment size with equivalent url size
                extra_bytes += num_attachments * ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES
                # -- remove attachments->data key to calculate data size
                apparent_body = copy.deepcopy(event)
                for attach_data in apparent_body["properties"]["$attachments"]:
                    del attach_data["data"]
                # ----
            else:
                # if auto upload is not enabled, attachment data will be passed as it is.
                pass

    # ---
    body_size = len(json.dumps(apparent_body, ensure_ascii=False).encode('utf-8'))
    apparent_size = body_size + extra_bytes
    # --
    return apparent_size


def get_apparent_identity_event_size(event: Dict) -> int:
    body_size = len(json.dumps(event, ensure_ascii=False).encode('utf-8'))
    return body_size


def get_apparent_list_broadcast_body_size(body: Dict) -> int:
    body_size = len(json.dumps(body, ensure_ascii=False).encode('utf-8'))
    return body_size


def validate_workflow_body_schema(body: Dict) -> Dict:
    # --- In case data is not provided, set it to empty dict
    if body.get("data") is None:
        body["data"] = {}
    if not isinstance(body["data"], dict):
        raise InputValueError("data must be a dictionary")
    # --------------------------------
    schema_validator = _get_schema_validator('workflow')
    try:
        schema_validator.validate(body)
    except jsonschema.exceptions.ValidationError as ve:
        raise SuprsendValidationError(ve.message)
    return body


def validate_track_event_schema(body: Dict) -> Dict:
    # --- In case props is not provided, set it to empty dict
    if body.get("properties") is None:
        body["properties"] = {}
    # --------------------------------
    schema_validator = _get_schema_validator('event')
    try:
        schema_validator.validate(body)
    except jsonschema.exceptions.ValidationError as ve:
        raise SuprsendValidationError(ve.message)
    return body


def validate_list_broadcast_body_schema(body: Dict) -> Dict:
    # --- In case data is not provided, set it to empty dict
    if body.get("data") is None:
        body["data"] = {}
    if not isinstance(body["data"], dict):
        raise InputValueError("data must be a dictionary")
    # --------------------------------
    schema_validator = _get_schema_validator('list_broadcast')
    try:
        schema_validator.validate(body)
    except jsonschema.exceptions.ValidationError as ve:
        raise SuprsendValidationError(ve.message)
    return body


def invalid_record_json(failed_record, err):
    if isinstance(err, (InputValueError,)):
        err_str = str(err)
    else:
        # includes SuprsendValidationError,
        # OR any other error
        err_str = traceback.format_exc()
    # ------
    rec = {"record": failed_record, "error": err_str, "code": 500}
    return rec
