from datetime import datetime, timezone
from typing import Dict, Union

import requests
import urllib.parse

from .constants import (
    HEADER_DATE_FMT,
)
from .exception import SuprsendAPIException, SuprsendValidationError
from .signature import get_request_signature
from .object_edit import ObjectEdit


class ObjectsApi:
    def __init__(self, config):
        self.config = config
        self.list_url = "{}v1/object/".format(self.config.base_url)
        self.bulk_url = "{}v1/bulk/object/".format(self.config.base_url)

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.config.user_agent,
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
        }

    def _validate_object_type(self, object_type: str):
        if not object_type or not isinstance(object_type, (str,)) or not object_type.strip():
            raise SuprsendValidationError("missing object_type")
        return object_type.strip()

    def _validate_object_id(self, object_id: str):
        if not object_id or not isinstance(object_id, (str,)) or not object_id.strip():
            raise SuprsendValidationError("missing object_id")
        return object_id.strip()

    def list(self, object_type: str, options: Dict = None) -> Dict:
        object_type = self._validate_object_type(object_type)
        object_type_encoded = urllib.parse.quote_plus(object_type)
        encoded_options = urllib.parse.urlencode((options or {}))
        #
        url = "{}{}/{}".format(self.list_url, object_type_encoded, (f"?{encoded_options}" if encoded_options else ""))
        headers = self.__get_headers()
        # ---
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def detail_url(self, object_type: str, object_id: str) -> str:
        object_type = self._validate_object_type(object_type)
        object_type_encoded = urllib.parse.quote_plus(object_type)
        # --
        object_id = self._validate_object_id(object_id)
        object_id_encoded = urllib.parse.quote_plus(object_id)
        # --
        url = f"{self.list_url}{object_type_encoded}/{object_id_encoded}/"
        return url

    def get(self, object_type: str, object_id: str) -> Dict:
        url = self.detail_url(object_type, object_id)
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def upsert(self, object_type: str, object_id: str, payload: Dict = None) -> Dict:
        url = self.detail_url(object_type, object_id)
        payload = payload or {}
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "POST", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def edit(self, edit_ins_or_object_type: Union[ObjectEdit, str], object_id: str = None, edit_payload: Dict = None) -> Dict:
        if isinstance(edit_ins_or_object_type, ObjectEdit):
            edit_ins = edit_ins_or_object_type
            edit_ins.validate_body()
            payload = edit_ins.get_payload()
            url = self.detail_url(edit_ins.object_type, edit_ins.object_id)
        else:
            object_type = edit_ins_or_object_type
            payload = edit_payload or {}
            url = self.detail_url(object_type, object_id)
        # ---
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "PATCH", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete(self, object_type: str, object_id: str) -> Dict:
        url = self.detail_url(object_type, object_id)
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "DELETE", "", headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def bulk_delete(self, object_type: str, payload: Dict) -> Dict:
        """
        payload: {"object_ids": ["id1", "id2"]}
        :param object_type:
        :param payload:
        :return:
        """
        object_type = self._validate_object_type(object_type)
        object_type_encoded = urllib.parse.quote_plus(object_type)
        url = "{}{}/".format(self.bulk_url, object_type_encoded)
        payload = payload or {}
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "DELETE", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def get_subscriptions(self, object_type: str, object_id: str, options: Dict = None) -> Dict:
        encoded_options = urllib.parse.urlencode((options or {}))
        _detail_url = self.detail_url(object_type, object_id)
        url = "{}subscription/{}".format(_detail_url, (f"?{encoded_options}" if encoded_options else ""))
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def create_subscriptions(self, object_type: str, object_id: str, payload: Dict) -> Dict:
        """
        payload: {
            "recipients": ["distinct_id1", {"object_type": "type1", "id": "id1"},],
            "properties": {"type": "admin"}
        }
        :param object_type:
        :param object_id:
        :param payload:
        :return:
        """
        _detail_url = self.detail_url(object_type, object_id)
        url = "{}subscription/".format(_detail_url)
        payload = payload or {}
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "POST", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete_subscriptions(self, object_type: str, object_id: str, payload: Dict) -> Dict:
        """
        payload: {
            "recipients": ["distinct_id1", {"object_type": "type1", "id": "id1"},]
        }
        :param object_type:
        :param object_id:
        :param payload:
        :return:
        """
        _detail_url = self.detail_url(object_type, object_id)
        url = "{}subscription/".format(_detail_url)
        payload = payload or {}
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "DELETE", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def get_objects_subscribed_to(self, object_type: str, object_id: str, options: Dict = None) -> Dict:
        encoded_options = urllib.parse.urlencode((options or {}))
        _detail_url = self.detail_url(object_type, object_id)
        url = "{}subscribed_to/object/{}".format(_detail_url, (f"?{encoded_options}" if encoded_options else ""))
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def get_edit_instance(self, object_type: str, object_id: str) -> ObjectEdit:
        object_type = self._validate_object_type(object_type)
        object_id = self._validate_object_id(object_id)
        return ObjectEdit(self.config, object_type, object_id)
