import json
import platform
from datetime import datetime, timezone
from typing import Any, TypedDict, cast
from warnings import warn

import requests

from .attachment import get_attachment_json
from .brand import BrandsApi
from .constants import DEFAULT_URL, HEADER_DATE_FMT
from .event import Event, EventCollector
from .events_bulk import BulkEventsFactory
from .exception import InputValueError, SuprsendConfigError
from .logger import log_http_exchange, set_logging
from .messages_api import MessagesApi
from .objects_api import ObjectsApi
from .signature import get_request_signature
from .subscriber import SubscriberFactory
from .subscriber_list import SubscriberListsApi
from .subscribers_bulk import BulkSubscribersFactory
from .tenant import TenantsApi
from .users_api import UsersApi
from .version import __version__
from .workflow import Workflow, _WorkflowTrigger
from .workflow_api import WorkflowsApi
from .workflows_bulk import BulkWorkflowsFactory


class AppInfo(TypedDict):
    name: str
    version: str | None


def _format_app_info(info: AppInfo | None) -> str:
    if not info or not info.get("name"):
        return ""
    str = info["name"]
    if info.get("version"):
        str += "/%s" % (info["version"],)
    return str


class UserAgentBuilder(TypedDict):
    sdk: str
    sdk_version: str
    lang: str
    lang_version: str | None
    # server, android, ios, react-native, flutter, browser, macos
    platform: str
    # environment: web/mobile/desktop
    environment: str | None
    # linux / darwin / windows / android / ios
    os: str | None
    os_version: str | None
    # app_info: optional, can be set by user
    app_info: AppInfo | None
    # for mobile only (e.g "Pixel 8")
    device_model: str | None
    # For browser (js-sdk only)
    browser: str | None  # chrome/firebox/safari
    browser_version: str | None

    @classmethod  # type: ignore[misc]  # runtime classmethod on a TypedDict
    def build_user_agent(cls, app_info: AppInfo | None) -> tuple[str, str]:
        try:
            uname = platform.uname()
            _os, _os_version = (uname.system or "").lower(), (uname.release or "").lower()
        except Exception:
            _os, _os_version = "(disabled)", "(disabled)"
        ins = cls(
            sdk="suprsend-py-sdk",
            sdk_version=__version__,
            lang="python",
            lang_version=platform.python_version(),
            platform="server",
            os=_os,
            os_version=_os_version,
            app_info=app_info,
        )
        cua = json.dumps(ins)
        # ---
        user_agent = "suprsend-py-sdk/{} (python/{}; {})".format(ins["sdk_version"], ins["lang_version"], ins["os"])
        app_info_str = _format_app_info(app_info)
        if app_info_str:
            user_agent += f" ({app_info_str})"
        # ---
        return user_agent, cua


class Suprsend:
    """
    - Workspace key + secret (HMAC)
     supr_client = Suprsend("__workspace_key__", "__workspace_secret__")
    - HTTP API Key (Bearer)
     supr_client = Suprsend.with_workspace_api_key("__workspace_uid__", "__api_key__")
    - Instance with debug on
     supr_client = Suprsend("__workspace_key__", "__workspace_secret__", debug=True)
    - Instance with custom base-url
     supr_client = Suprsend("__workspace_key__", "__workspace_secret__", base_url="https://example.com/", debug=False)
    """

    def __init__(
        self,
        workspace_key: str,
        workspace_secret: str,
        base_url: str | None = None,
        debug: bool = False,
        app_info: AppInfo | None = None,
        **kwargs: Any,
    ) -> None:
        self._init(
            "ws_key_secret",
            workspace_key=workspace_key,
            workspace_secret=workspace_secret,
            base_url=base_url,
            debug=debug,
            app_info=app_info,
            **kwargs,
        )

    @classmethod
    def with_workspace_api_key(
        cls,
        workspace_uid: str,
        api_key: str,
        base_url: str | None = None,
        debug: bool = False,
        app_info: AppInfo | None = None,
        **kwargs: Any,
    ) -> "Suprsend":
        """
        Authenticate with an HTTP API Key (Bearer token).

        Workspace UID: SuprSend dashboard -> Settings -> General -> Workspace UID.
        API Key: SuprSend dashboard -> Developers -> API Keys.
        """
        inst = cls.__new__(cls)
        inst._init(
            "api_key",
            workspace_uid=workspace_uid,
            api_key=api_key,
            base_url=base_url,
            debug=debug,
            app_info=app_info,
            **kwargs,
        )
        return inst

    def _init(
        self,
        auth_method: str,
        *,
        workspace_key: str | None = None,
        workspace_secret: str | None = None,
        workspace_uid: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        debug: bool = False,
        app_info: AppInfo | None = None,
        **kwargs: Any,
    ) -> None:
        self.auth_method = auth_method
        self.workspace_key = workspace_key
        self.workspace_secret = workspace_secret
        self.workspace_uid = workspace_uid
        self.api_key = api_key
        self.__do_init(base_url=base_url, debug=debug, app_info=app_info, **kwargs)

    def __do_init(self, *, base_url: str | None, debug: bool, app_info: AppInfo | None, **kwargs: Any) -> None:
        #
        self.user_agent, self.client_user_agent = UserAgentBuilder.build_user_agent(  # type: ignore[attr-defined]
            app_info
        )
        #
        self.base_url = self.__get_base_url(base_url)
        # ---
        self.__validate()
        self.debug = bool(debug)
        set_logging(self.debug)
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
        self.tenants = TenantsApi(self)
        self.brands = BrandsApi(self)
        self.workflows = WorkflowsApi(self)
        self.objects = ObjectsApi(self)
        self.users = UsersApi(self)
        self.messages = MessagesApi(self)
        # --
        self.subscriber_lists = SubscriberListsApi(self)

    @property
    def bulk_workflows(self) -> BulkWorkflowsFactory:
        return self._bulk_workflows

    @property
    def bulk_events(self) -> BulkEventsFactory:
        return self._bulk_events

    @property
    def bulk_users(self) -> BulkSubscribersFactory:
        return self._bulk_users

    @property
    def user(self) -> SubscriberFactory:
        return self._user

    def workspace_identifier(self) -> str:
        if self.auth_method == "ws_key_secret":
            return cast(str, self.workspace_key)
        elif self.auth_method == "api_key":
            return cast(str, self.workspace_uid)
        else:
            return ""

    def default_headers(self) -> dict[str, Any]:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.user_agent,
            "X-Suprsend-Client-User-Agent": self.client_user_agent,
        }

    def prepare_request(self, method: str, url: str, body: Any = None) -> tuple[dict[str, Any], str]:
        headers = self.default_headers()
        if self.auth_method == "ws_key_secret":
            headers["Date"] = datetime.now(timezone.utc).strftime(HEADER_DATE_FMT)
            content_txt, sig = get_request_signature(url, method, body, headers, cast(str, self.workspace_secret))
            headers["Authorization"] = "{}:{}".format(self.workspace_key, sig)
        elif self.auth_method == "api_key":
            if method == "GET" or body == "" or body is None:
                content_txt = ""
            else:
                content_txt = json.dumps(body, ensure_ascii=False)
            headers["Authorization"] = "Bearer {}".format(self.api_key)
        else:
            raise SuprsendConfigError("Invalid auth_method")
        return headers, content_txt

    def request(self, method: str, url: str, body: Any = None) -> requests.Response:
        headers, content_txt = self.prepare_request(method, url, body)
        method_u = method.upper()
        kwargs: dict[str, Any] = {"headers": headers}
        if method_u not in ("GET", "HEAD"):
            kwargs["data"] = content_txt.encode("utf-8")
        # ---
        try:
            resp = requests.request(method_u, url, **kwargs)
        except Exception as ex:
            log_http_exchange(method_u, url, headers, content_txt, error=ex)
            raise
        log_http_exchange(method_u, url, headers, content_txt, resp=resp)
        return resp

    @staticmethod
    def __get_base_url(base_url: str | None) -> str:
        # ---- strip
        if base_url:
            base_url = base_url.strip()
        # ---- if url not passed, set url based on server env
        if not base_url:
            base_url = DEFAULT_URL
        # ---- check url ends with /
        base_url = base_url.strip()
        if base_url[len(base_url) - 1] != "/":
            base_url = base_url + "/"
        return base_url

    def __validate(self) -> None:
        if self.auth_method == "ws_key_secret":
            if not self.workspace_key:
                raise SuprsendConfigError("Missing workspace_key")
            if not self.workspace_secret:
                raise SuprsendConfigError("Missing workspace_secret")
        elif self.auth_method == "api_key":
            if not self.workspace_uid:
                raise SuprsendConfigError("Missing workspace_uid")
            if not self.api_key:
                raise SuprsendConfigError("Missing api_key")
        else:
            raise SuprsendConfigError("Invalid auth_method")
        if not self.base_url:
            raise SuprsendConfigError("Missing base_url")

    def add_attachment(
        self, body: dict[str, Any], file_path: str, file_name: str | None = None, ignore_if_error: bool = False
    ) -> dict[str, Any]:
        warn(
            'This method is deprecated. Use "WorkflowTriggerRequest.add_attachment()" instead',
            DeprecationWarning,
            stacklevel=2,
        )
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

    def trigger_workflow(self, data: Workflow | dict[str, Any]) -> dict[str, Any]:
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
        # warn('This method will be deprecated. Use client.workflows.trigger(WorkflowTriggerRequest) instead',
        #      DeprecationWarning, stacklevel=2)
        if isinstance(data, Workflow):
            wf_ins = data
        else:
            wf_ins = Workflow(data, idempotency_key=None, tenant_id=None)
        # -----
        return self._workflow_trigger.trigger(wf_ins)

    def track(
        self,
        distinct_id: str,
        event_name: str,
        properties: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        tenant_id: str | None = None,
        brand_id: str | None = None,
    ) -> dict[str, Any]:
        """
        :param distinct_id:
        :param event_name:
        :param properties:
        :param idempotency_key:
        :param tenant_id:
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
        warn('This method is deprecated. Use "track_event(Event)" instead', DeprecationWarning, stacklevel=2)
        if not tenant_id:
            tenant_id = brand_id
        # ---
        event = Event(distinct_id, event_name, properties, idempotency_key=idempotency_key, tenant_id=tenant_id)
        return self._eventcollector.collect(event)

    def track_event(self, event: Event) -> dict[str, Any]:
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
