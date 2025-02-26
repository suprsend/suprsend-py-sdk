from datetime import datetime, timezone
from typing import Dict, Union
import requests
import urllib.parse

from .constants import (
    HEADER_DATE_FMT,
)
from .exception import SuprsendAPIException, SuprsendValidationError
from .signature import get_request_signature
from .user_edit import UserEdit
from .users_edit_bulk import BulkUsersEdit


class UsersApi:
    def __init__(self, config):
        self.config = config
        self.list_url = "{}v1/user/".format(self.config.base_url)
        self.bulk_url = "{}v1/bulk/user/".format(self.config.base_url)

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.config.user_agent,
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
        }

    def list(self, options: Dict = None) -> Dict:
        encoded_options = urllib.parse.urlencode((options or {}))
        url = "{}{}".format(self.list_url, (f"?{encoded_options}" if encoded_options else ""))
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

    def _validate_distinct_id(self, distinct_id: str) -> str:
        if not distinct_id or not isinstance(distinct_id, (str,)) or not distinct_id.strip():
            raise SuprsendValidationError("missing distinct_id")
        return distinct_id.strip()

    def detail_url(self, distinct_id: str) -> str:
        distinct_id = self._validate_distinct_id(distinct_id)
        distinct_id_encoded = urllib.parse.quote_plus(distinct_id)
        return f"{self.list_url}{distinct_id_encoded}/"

    def get(self, distinct_id: str) -> Dict:
        url = self.detail_url(distinct_id)
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def upsert(self, distinct_id: str, payload: Dict = None) -> Dict:
        url = self.detail_url(distinct_id)
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

    def async_edit(self, edit_instance: UserEdit) -> Dict:
        if not edit_instance:
            raise SuprsendValidationError("instance is required")
        edit_instance.validate_body()
        a_payload = edit_instance.get_async_payload()
        edit_instance.validate_payload_size(a_payload)
        # --- Signature and Authorization-header
        url = "{}event/".format(self.config.base_url)
        headers = self.__get_headers()
        content_txt, sig = get_request_signature(url, "POST", a_payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        # if no error, return success response
        return {"success": True, "status": "success", "status_code": resp.status_code, "message": resp.text}

    def edit(self, edit_ins_or_distinct_id: Union[UserEdit, str], edit_payload: Dict = None) -> Dict:
        if isinstance(edit_ins_or_distinct_id, UserEdit):
            edit_ins = edit_ins_or_distinct_id
            edit_ins.validate_body()
            payload = edit_ins.get_payload()
            url = self.detail_url(edit_ins.distinct_id)
        else:
            distinct_id = edit_ins_or_distinct_id
            payload = edit_payload or {}
            url = self.detail_url(distinct_id)
        # ----
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "PATCH", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def merge(self, distinct_id: str, from_user_id: str) -> Dict:
        url = "{}merge/".format(self.detail_url(distinct_id))
        payload = {"from_user_id": from_user_id}
        headers = self.__get_headers()
        # ---
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "POST", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete(self, distinct_id: str) -> Dict:
        url = self.detail_url(distinct_id)
        headers = self.__get_headers()
        # ---
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "DELETE", "", headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def bulk_delete(self, payload: Dict) -> Dict:
        """
        payload: {"distinct_ids": ["id1", "id2"]}
        :param payload:
        :return:
        """
        payload = payload or {}
        url = self.bulk_url
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "DELETE", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def get_objects_subscribed_to(self, distinct_id: str, options: Dict = None) -> Dict:
        encoded_options = urllib.parse.urlencode((options or {}))
        _detail_url = self.detail_url(distinct_id)
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

    def get_lists_subscribed_to(self, distinct_id: str, options: Dict = None) -> Dict:
        encoded_options = urllib.parse.urlencode((options or {}))
        _detail_url = self.detail_url(distinct_id)
        url = "{}subscribed_to/list/{}".format(_detail_url, (f"?{encoded_options}" if encoded_options else ""))
        headers = self.__get_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def get_edit_instance(self, distinct_id: str) -> UserEdit:
        distinct_id = self._validate_distinct_id(distinct_id)
        return UserEdit(self.config, distinct_id)

    def get_bulk_edit_instance(self) -> BulkUsersEdit:
        return BulkUsersEdit(self.config)
