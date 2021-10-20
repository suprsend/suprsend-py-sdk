import os
import base64
import magic

from typing import List, Dict
from .exception import SuprsendConfigError
from .workflow import WorkflowTrigger
from .request_log import set_logging


class Suprsend:
    """
    Entry point of SDK. Follow below Steps:
    1. create instance
        supr_client = Suprsend("__env_key__", "__env_secret__")
    2. Trigger required method
        workflow_body = {...}
        response = supr_client.trigger_workflow(workflow_body)
    """
    def __init__(self, env_key: str, env_secret: str, base_url: str = None, debug: bool = False, **kwargs):
        self.env_key = env_key
        self.env_secret = env_secret
        self.base_url = self.__get_url(base_url, kwargs)
        # include cryptographic signature
        self.auth_enabled = (kwargs.get('auth_enabled') is not False)
        self.include_signature_param = (kwargs.get('include_signature_param') is not False)
        # ---
        self.__validate()
        # --- set logging level for http request
        req_log_level = 1 if debug else 0
        set_logging(req_log_level)

    DEFAULT_URL = "https://hub.suprsend.com/"
    DEFAULT_UAT_URL = "https://collector-staging.suprsend.workers.dev/"

    def __get_url(self, base_url, kwargs):
        # ---- strip
        if base_url:
            base_url = base_url.strip()
        # ---- if url not passed, set url based on server env
        if not base_url:
            if kwargs.get("is_uat", False):
                base_url = self.DEFAULT_UAT_URL
            else:
                base_url = self.DEFAULT_URL
        # ---- check url ends with /
        base_url = base_url.strip()
        if base_url[len(base_url) - 1] != "/":
            base_url = base_url + "/"
        return base_url

    def __validate(self):
        if not self.env_key:
            raise SuprsendConfigError("Missing env_key")
        if not self.env_secret:
            raise SuprsendConfigError("Missing env_secret")
        if not self.base_url:
            raise SuprsendConfigError("Missing base_url")

    def get_attachment_json_for_file(self, file_path: str) -> Dict:
        # Ensure that path is expanded and absolute
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        found = os.path.isfile(abs_path)
        if not found:
            return {
                "success": False,
                "error": "Not a file: {}".format(abs_path),
                "attachment": {}
            }
        # Get attachment json
        try:
            with open(abs_path, "rb") as f:
                file_name = os.path.basename(abs_path)
                mime_type = magic.from_file(abs_path, mime=True)
                # base64 encoded string
                b64encoded = base64.b64encode(f.read())
                b64data = b64encoded.decode()
                return {
                    "success": True,
                    "error": None,
                    "attachment": {
                        "filename": file_name,
                        "contentType": mime_type,
                        "data": b64data,
                    }
                }
        except FileNotFoundError as fnfe:
            return {
                "success": False,
                "error": str(fnfe),
                "attachment": {}
            }

    def trigger_workflow(self, data: Dict) -> Dict:
        """
        :param data:
        :return: {
            "success": true/false,
            "status": 202/401/500,
            "message": "message",
        }
        :except:
            - SuprsendConfigError (if proper value for env_key and env_secret not set
            - SuprsendValidationError (if post-data is invalid.)
        """
        wt = WorkflowTrigger(self, data)
        wt.validate_data()
        return wt.execute_workflow()
