import os
import json
import jsonschema
from .exception import SuprsendMissingSchema, SuprsendInvalidSchema


# Cached json schema
__JSON_SCHEMAS = dict()


def _get_schema_validator(schema_name: str):
    schema_body = __JSON_SCHEMAS.get(schema_name)
    if not schema_body:
        schema_body = __load_json_schema(schema_name)
        __JSON_SCHEMAS[schema_name] = schema_body
    return schema_body


def __load_json_schema(schema_name: str):
    here = os.path.dirname(os.path.abspath(__file__))
    rel_path = "request_json/{}.json".format(schema_name)
    file_path = os.path.join(here, rel_path)
    with open(file_path) as f:
        schema_body = json.load(f)
        if not schema_body:
            raise SuprsendMissingSchema(schema_name)
        try:
            jsonschema.Draft7Validator.check_schema(schema_body)
        except jsonschema.exceptions.SchemaError as se:
            raise SuprsendInvalidSchema(se.message)
        return jsonschema.Draft7Validator(schema_body)
