import platform

from typing import List, Dict
from .version import __version__
from .constants import (DEFAULT_URL, DEFAULT_UAT_URL)
from .exception import SuprsendConfigError, InputValueError
from .attachment import get_attachment_json
from .workflow import Workflow, _WorkflowTrigger
from .request_log import set_logging
from .workflows_bulk import BulkWorkflowsFactory
from .events_bulk import BulkEventsFactory
from .subscribers_bulk import BulkSubscribersFactory
from .subscriber import SubscriberFactory
from .subscriber_list import SubscriberListsApi
from .event import Event, EventCollector
from .brand import BrandsApi


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
        # ---
        self.__validate()
        # --- set logging level for http request
        self.req_log_level = 1 if debug else 0
        set_logging(self.req_log_level)
        #
        self._workflow_trigger = _WorkflowTrigger(self)
        self._eventcollector = EventCollector(self)
        # -- bulk instances
        self._bulk_workflows = BulkWorkflowsFactory(self)
        self._bulk_events = BulkEventsFactory(self)
        self._bulk_users = BulkSubscribersFactory(self)
        # --
        self._user = SubscriberFactory(self)
        # --
        self.brands = BrandsApi(self)
        self.subscriber_lists = SubscriberListsApi(self)

    @property
    def bulk_workflows(self):
        return self._bulk_workflows

    @property
    def bulk_events(self):
        return self._bulk_events

    @property
    def bulk_users(self):
        return self._bulk_users

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

    def add_attachment(self, body: Dict, file_path: str, file_name: str = None, ignore_if_error: bool = False) -> Dict:
        # if data key not present, add it and set value={}.
        if body.get("data") is None:
            body["data"] = {}
        if not isinstance(body, dict):
            raise InputValueError("data must be a dictionary")
        # --------
        attachment = get_attachment_json(file_path, file_name, ignore_if_error)
        # --- add the attachment to body->data->$attachments
        if body["data"].get("$attachments") is None:
            body["data"]["$attachments"] = []
        #
        body["data"]["$attachments"].append(attachment)
        return body

    def trigger_workflow(self, data) -> Dict:
        """
        :param data:
        :return: {
            "success": true/false,
            "status": "success"/"fail",
            "message": "message",
            "status_code": 202/401/500,
        }
        :except:
            - SuprsendValidationError
        """
        if isinstance(data, Workflow):
            wf_ins = data
        else:
            wf_ins = Workflow(data, idempotency_key=None, brand_id=None)
        # -----
        return self._workflow_trigger.trigger(wf_ins)

    def track(self, distinct_id: str, event_name: str, properties: Dict = None,
              idempotency_key: str = None, brand_id: str = None) -> Dict:
        """
        :param distinct_id:
        :param event_name:
        :param properties:
        :param idempotency_key:
        :param brand_id:
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
        event = Event(distinct_id, event_name, properties, idempotency_key=idempotency_key, brand_id=brand_id)
        return self._eventcollector.collect(event)

    def track_event(self, event: Event) -> Dict:
        """
        :param event: suprsend.Event
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
        if not isinstance(event, Event):
            raise InputValueError("argument must be an instance of suprsend.Event")
        return self._eventcollector.collect(event)
