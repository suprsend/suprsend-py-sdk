from typing import Dict, List

import requests
import urllib.parse

from .exception import SuprsendAPIException, SuprsendValidationError
from .signature import get_request_signature

_MULTI_VALUE_KEYS = ("recipient_id", "status", "category")


class MessagesApi:
    def __init__(self, config):
        self.config = config
        self.__list_url = "{}v1/message/".format(self.config.base_url)
        self.__bulk_patch_url = "{}v1/bulk/message/".format(self.config.base_url)

    def __build_list_params(self, options: Dict) -> Dict:
        params = {}
        for key, val in options.items():
            if key in _MULTI_VALUE_KEYS:
                params["{}[]".format(key)] = val if isinstance(val, list) else [val]
            else:
                params[key] = val
        return params

    def list(self, options: Dict = None) -> Dict:
        params = self.__build_list_params(options or {})
        encoded_params = urllib.parse.urlencode(params, doseq=True)
        url = "{}{}".format(self.__list_url, ("?{}".format(encoded_params) if encoded_params else ""))
        headers = self.config.default_headers()
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def bulk_update(self, messages: List[Dict]) -> Dict:
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
        headers = self.config.default_headers()
        content_txt, sig = get_request_signature(url, "PATCH", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        resp = requests.patch(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    # def _validate_message_id(self, message_id: str) -> str:
    #     if not message_id or not isinstance(message_id, str) or not message_id.strip():
    #         raise SuprsendValidationError("missing message_id")
    #     return message_id.strip()

    # def get_content(self, message_id: str) -> Dict:
    #     message_id = self._validate_message_id(message_id)
    #     message_id_encoded = urllib.parse.quote_plus(message_id)
    #     url = "{}/{}/content".format(self.__list_url, message_id_encoded)
    #     headers = self.config.default_headers()
    #     content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
    #     headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
    #     resp = requests.get(url, headers=headers)
    #     if resp.status_code >= 400:
    #         raise SuprsendAPIException(resp)
    #     return resp.json()
