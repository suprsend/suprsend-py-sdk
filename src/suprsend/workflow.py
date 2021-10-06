from datetime import datetime, timezone
import requests
import jsonschema
from urllib.parse import quote_plus
import json
from .exception import SuprsendValidationError, SuprsendInvalidSchema
from .request_schema import _get_schema
from .signature import get_request_signature


# In TZ Format: "%a, %d %b %Y %H:%M:%S %Z"
HEADER_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class WorkflowTrigger:
    def __init__(self, config, data):
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
        url_formatted = url_template.format(self.config.base_url, self.config.env_key)
        # ---
        # self.url = quote_plus(url_formatted)
        return url_formatted

    def __get_headers(self):
        return {
            "Content-Type": "application/json",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
        }

    def execute_workflow(self):
        headers = self.__get_headers()
        # Based on whether signature is required or not, add Authorization header
        if self.config.auth_enabled:
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(self.url, 'POST', self.data, headers, self.config.env_secret)
            headers["Authorization"] = "{}:{}".format(self.config.env_key, sig)
        else:
            content_txt = json.dumps(self.data)
        # -----
        resp = requests.post(self.url,
                             data=content_txt,
                             headers=headers)

        success = resp.status_code // 100 == 2
        return {
            "success": success,
            "status": resp.status_code,
            "message": resp.text,
        }

    def validate_data(self):
        schema = _get_schema('workflow')
        try:
            # jsonschema.validate(instance, schema, cls=None, *args, **kwargs)
            jsonschema.validate(self.data, schema)
        except jsonschema.exceptions.SchemaError as se:
            raise SuprsendInvalidSchema(se.message)
        except jsonschema.exceptions.ValidationError as ve:
            raise SuprsendValidationError(ve.message)
        return self.data
