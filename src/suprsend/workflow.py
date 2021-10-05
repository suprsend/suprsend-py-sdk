from datetime import datetime, timezone
import requests
import jsonschema

from .request_schema import _get_schema
from .signature import create_request_signature

# TZ: "%a, %d %b %Y %H:%M:%S %Z"
HEADER_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class WorkflowTrigger:
    def __init__(self, config, data):
        self.config = config
        self.data = data

    def __get_headers(self):
        return {
            "Content-Type": "application/json",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
        }

    def execute_workflow(self):
        import pdb; pdb.set_trace()
        headers = self.__get_headers()
        # Based on whether signature is required or not, header might differ
        signature_applicable = True
        if signature_applicable:
            url_template = "{}{}/trigger/?signature=true"
            url = url_template.format(self.config.base_url, self.config.env_key)
            # Signature and Authorization-header
            sig = create_request_signature(url, 'POST', self.data, headers, self.config.env_secret)
            headers["Authorization"] = "{}: {}".format(self.config.env_key, sig)
        else:
            url_template = "{}{}/trigger/?signature=false"
            url = url_template.format(self.config.base_url, self.config.env_key)

        # -----
        r = requests.post(url, data=self.data, headers=headers)
        if r.status_code == 202:
            return r.status_code, r.reason
        else:
            return r.status_code, r.reason

    def validate_data(self):
        schema = _get_schema('workflow')
        # jsonschema.validate(instance, schema, cls=None, *args, **kwargs)
        try:
            jsonschema.validate(self.data, schema)
        except jsonschema.exceptions.SchemaError as se:
            pass
        except jsonschema.exceptions.ValidationError as ve:
            pass
        return self.data
