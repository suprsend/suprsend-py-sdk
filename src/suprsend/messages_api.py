from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from .exception import SuprsendAPIException, SuprsendValidationError
from .utils import urlencode_query

if TYPE_CHECKING:
    from .sdkinstance import Suprsend

_MULTI_VALUE_KEYS = ("recipient_id", "status", "category")


class MessagesApi:
    def __init__(self, config: "Suprsend") -> None:
        self.config = config
        self.__list_url = "{}v1/message/".format(self.config.base_url)
        self.__bulk_patch_url = "{}v1/bulk/message/".format(self.config.base_url)

    def __build_list_params(self, options: Dict[str, Any]) -> Dict[str, Any]:
        params = {}
        for key, val in options.items():
            if key in _MULTI_VALUE_KEYS:
                params["{}[]".format(key)] = val if isinstance(val, list) else [val]
            else:
                params[key] = val
        return params

    def list(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = self.__build_list_params(options or {})
        encoded_params = urlencode_query(params, doseq=True)
        url = "{}{}".format(self.__list_url, ("?{}".format(encoded_params) if encoded_params else ""))
        resp = self.config.request("GET", url, None)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return cast(Dict[str, Any], resp.json())

    def bulk_update(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        list of messages with their id and action. e.g.
        messages = [{"message_id": "01KQVGPW9ZJKH6T5TSxxxxxxx", "action": "read"}]
        """
        for i, msg in enumerate(messages):
            if not msg.get("message_id"):
                raise SuprsendValidationError("messages[{}]: missing message_id".format(i))
            if not msg.get("action"):
                raise SuprsendValidationError("messages[{}]: missing action".format(i))
        payload = {"messages": messages}
        url = self.__bulk_patch_url
        resp = self.config.request("PATCH", url, payload)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return cast(Dict[str, Any], resp.json())

    # def _validate_message_id(self, message_id: str) -> str:
    #     if not message_id or not isinstance(message_id, str) or not message_id.strip():
    #         raise SuprsendValidationError("missing message_id")
    #     return message_id.strip()

    # def get_content(self, message_id: str) -> Dict:
    #     message_id = self._validate_message_id(message_id)
    #     message_id_encoded = urlencode_path_param(message_id)
    #     url = "{}/{}/content".format(self.__list_url, message_id_encoded)
    #     resp = self.config.request("GET", url, None)
    #     if resp.status_code >= 400:
    #         raise SuprsendAPIException(resp)
    #     return resp.json()
