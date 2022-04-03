import os
import platform
import base64
import magic

from typing import List, Dict
from .version import __version__
from .constants import (DEFAULT_URL, DEFAULT_UAT_URL)
from .exception import SuprsendConfigError
from .workflow import WorkflowTrigger
from .request_log import set_logging
from .workflow_batch import WorkflowBatchFactory
from .identity import UserIdentityFactory
from .event import EventCollector


class Suprsend:
    """
    - Basic instance
     supr_client = Suprsend("__workspace_key__", "__workspace_secret__")
    - Instance with debug on
     supr_client = Suprsend("__workspace_key__", "__workspace_secret__", debug=True)
    - Instance with custom base-url
     supr_client = Suprsend("__workspace_key__", "__workspace_secret__", base_url="https://example.com/", debug=False)
    """
    def __init__(self, workspace_key: str, workspace_secret: str, base_url: str = None, debug: bool = False, **kwargs):
        self.workspace_key = workspace_key
        self.workspace_secret = workspace_secret
        #
        self.sdk_version = __version__
        self.user_agent = "suprsend/{};python/{}".format(self.sdk_version, platform.python_version())
        #
        is_uat = kwargs.get("is_uat", False)
        self.base_url = self.__get_url(base_url, is_uat)
        # include cryptographic signature
        self.auth_enabled = (kwargs.get('auth_enabled') is not False)
        self.include_signature_param = (kwargs.get('include_signature_param') is not False)
        # ---
        self.__validate()
        # --- set logging level for http request
        self.req_log_level = 1 if debug else 0
        set_logging(self.req_log_level)
        #
        self._eventcollector = EventCollector(self)
        # -- instantiate batch
        self._workflow_batch = WorkflowBatchFactory(self)
        self._user = UserIdentityFactory(self)

    @property
    def workflow_batch(self):
        return self._workflow_batch

    @property
    def user(self):
        return self._user

    @staticmethod
    def __get_url(base_url, is_uat):
        # ---- strip
        if base_url:
            base_url = base_url.strip()
        # ---- if url not passed, set url based on server env
        if not base_url:
            base_url = DEFAULT_UAT_URL if is_uat else DEFAULT_URL
        # ---- check url ends with /
        base_url = base_url.strip()
        if base_url[len(base_url) - 1] != "/":
            base_url = base_url + "/"
        return base_url

    def __validate(self):
        if not self.workspace_key:
            raise SuprsendConfigError("Missing workspace_key")
        if not self.workspace_secret:
            raise SuprsendConfigError("Missing workspace_secret")
        if not self.base_url:
            raise SuprsendConfigError("Missing base_url")

    def add_attachment(self, body: Dict, file_path: str) -> Dict:
        # if data key not present, add it and set value={}.
        if body.get("data") is None:
            body["data"] = {}
        if not isinstance(body, dict):
            raise ValueError("data must be a dictionary")
        # --------
        attachment = self.__get_attachment_json_for_file(file_path)
        # --- add the attachment to body->data->$attachments
        if body["data"].get("$attachments") is None:
            body["data"]["$attachments"] = []
        #
        body["data"]["$attachments"].append(attachment)
        return body

    def __get_attachment_json_for_file(self, file_path: str) -> Dict:
        # Ensure that path is expanded and absolute
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        # Get attachment json
        with open(abs_path, "rb") as f:
            file_name = os.path.basename(abs_path)
            mime_type = magic.from_file(abs_path, mime=True)
            # base64 encoded string
            b64encoded = base64.b64encode(f.read())
            b64data = b64encoded.decode()
            return {
                "filename": file_name,
                "contentType": mime_type,
                "data": b64data,
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
            - SuprsendValidationError (if post-data is invalid.)
        """
        wt = WorkflowTrigger(self, data)
        wt.validate_data()
        return wt.execute_workflow()

    def track(self, distinct_id: str, event_name: str, properties: Dict = None) -> Dict:
        """
        :param distinct_id:
        :param event_name:
        :param properties:
        :return: {
            "success": True,
            "status": "success",
            "status_code": resp.status_code,
            "message": resp.text,
        }
        :except:
            - SuprsendValidationError (if post-data is invalid.)
            - ValueError
        """
        return self._eventcollector.collect(distinct_id, event_name, properties)
