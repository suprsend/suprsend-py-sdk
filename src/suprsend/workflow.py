import json

import requests
import jsonschema
from .config import Suprsend, _get_schema


def execute_workflow(config: Suprsend, data):
    url = config.base_url + config.env_key + "/trigger/"
    r = requests.post(url, data)
    if r.status_code == 202:
        return r.status_code, r.reason
    else:
        return r.status_code, r.reason


def validate_data(data):
    schema = _get_schema('workflow')

    # jsonschema.validate(instance, schema, cls=None, *args, **kwargs)
    jsonschema.validate(data, schema, )
    return {
        "name": data[""]
    }
