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
    def __init__(self, env_key: str, env_secret: str, post_url: str = None, debug: bool = False, **kwargs):
        self.env_key = env_key
        self.env_secret = env_secret
        self.base_url = self.__get_url(post_url, kwargs)
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

    def __get_url(self, post_url, kwargs):
        # ---- strip
        if post_url:
            post_url = post_url.strip()
        # ---- if url not passed, set url based on server env
        if not post_url:
            if kwargs.get("is_uat", False):
                post_url = self.DEFAULT_UAT_URL
            else:
                post_url = self.DEFAULT_URL
        # ---- check url ends with /
        post_url = post_url.strip()
        if post_url[len(post_url) - 1] != "/":
            post_url = post_url + "/"
        return post_url

    def __validate(self):
        if not self.env_key:
            raise SuprsendConfigError("Missing env_key")
        if not self.env_secret:
            raise SuprsendConfigError("Missing env_secret")
        if not self.base_url:
            raise SuprsendConfigError("Missing base_url")

    def trigger_workflow(self, data: dict) -> dict:
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
