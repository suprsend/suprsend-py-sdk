from typing import Dict
import copy
import json
import jsonschema

from .constants import (
    RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES,
    ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES
)
from .exception import SuprsendValidationError, SuprsendInvalidSchema
from .request_schema import _get_schema


def get_apparent_body_size(body: Dict) -> int:
    # ---
    extra_bytes = RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES
    apparent_body = body
    # ---
    if body.get("data") and body["data"].get("$attachments"):
        num_attachments = len(body["data"]["$attachments"])
        extra_bytes += num_attachments * ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES
        # -- remove attachments->data key to calculate data size
        apparent_body = copy.deepcopy(body)
        for attach_data in apparent_body["data"]["$attachments"]:
            del attach_data["data"]
    # ---
    body_size = len(json.dumps(apparent_body, ensure_ascii=False).encode('utf-8'))
    apparent_body_size = body_size + extra_bytes
    # --
    return apparent_body_size


def validate_workflow_body_schema(data: Dict) -> Dict:
    # --- In case data is not provided, set it to empty dict
    if data.get("data") is None:
        data["data"] = {}
    if not isinstance(data["data"], dict):
        raise ValueError("data must be a dictionary")
    # --------------------------------
    schema = _get_schema('workflow')
    try:
        # jsonschema.validate(instance, schema, cls=None, *args, **kwargs)
        jsonschema.validate(data, schema)
    except jsonschema.exceptions.SchemaError as se:
        raise SuprsendInvalidSchema(se.message)
    except jsonschema.exceptions.ValidationError as ve:
        raise SuprsendValidationError(ve.message)
    return data
