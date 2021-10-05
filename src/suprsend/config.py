from .exception import SuprsendConfigError
from .workflow import WorkflowTrigger


class Suprsend:
    DEFAULT_URL = "https://hub.suprsend.com/"

    def __init__(self, env_key, env_secret, post_url=None):
        self.env_key = env_key
        self.env_secret = env_secret
        if not post_url:
            post_url = self.DEFAULT_URL
        # -- check url ends with /
        post_url = post_url.strip()
        if post_url[len(post_url) - 1] != "/":
            post_url = post_url + "/"
        # ---
        self.base_url = post_url
        #
        self.__validate()

    def __validate(self):
        if not self.env_key:
            raise SuprsendConfigError("Missing env_key")
        if not self.env_secret:
            raise SuprsendConfigError("Missing env_secret")
        if not self.base_url:
            raise SuprsendConfigError("Missing base_url")

    def trigger_workflow(self, data: dict):
        wt = WorkflowTrigger(self, data)
        wt.validate_data()
        wt.execute_workflow()
