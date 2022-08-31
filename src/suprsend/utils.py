from typing import Dict
import copy
import json
import jsonschema

from .constants import (
    WORKFLOW_RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES,
    ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES,
    ATTACHMENT_UPLOAD_ENABLED, ALLOW_ATTACHMENTS_IN_BATCH,
)
from .exception import SuprsendValidationError, SuprsendInvalidSchema
from .request_schema import _get_schema


def get_apparent_workflow_body_size(body: Dict, is_part_of_batch: bool) -> int:
    # ---
    extra_bytes = WORKFLOW_RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES
    apparent_body = body
    # ---
    if body.get("data") and body["data"].get("$attachments"):
        num_attachments = len(body["data"]["$attachments"])
        if is_part_of_batch:
            if ALLOW_ATTACHMENTS_IN_BATCH:
                # if attachment is allowed in batch, then calculate size based on whether auto Upload is enabled
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


def get_apparent_event_size(event: Dict, is_part_of_batch: bool) -> int:
    # ---
    extra_bytes = 0
    apparent_body = event
    # ---
    if event.get("properties") and event["properties"].get("$attachments"):
        num_attachments = len(event["properties"]["$attachments"])
        if is_part_of_batch:
            if ALLOW_ATTACHMENTS_IN_BATCH:
                # if attachment is allowed in batch, then calculate size based on whether auto Upload is enabled
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


def validate_workflow_body_schema(body: Dict) -> Dict:
    # --- In case data is not provided, set it to empty dict
    if body.get("data") is None:
        body["data"] = {}
    if not isinstance(body["data"], dict):
        raise ValueError("data must be a dictionary")
    # --------------------------------
    schema = _get_schema('workflow')
    try:
        # jsonschema.validate(instance, schema, cls=None, *args, **kwargs)
        jsonschema.validate(body, schema)
    except jsonschema.exceptions.SchemaError as se:
        raise SuprsendInvalidSchema(se.message)
    except jsonschema.exceptions.ValidationError as ve:
        raise SuprsendValidationError(ve.message)
    return body


def validate_track_event_schema(body: Dict) -> Dict:
    # --- In case props is not provided, set it to empty dict
    if body.get("properties") is None:
        body["properties"] = {}
    # --------------------------------
    schema = _get_schema('event')
    try:
        # jsonschema.validate(instance, schema, cls=None, *args, **kwargs)
        jsonschema.validate(body, schema)
    except jsonschema.exceptions.SchemaError as se:
        raise SuprsendInvalidSchema(se.message)
    except jsonschema.exceptions.ValidationError as ve:
        raise SuprsendValidationError(ve.message)
    return body
