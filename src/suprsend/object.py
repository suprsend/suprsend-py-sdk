from datetime import datetime, timezone
from typing import Dict

import requests
import urllib.parse


from .constants import (
    HEADER_DATE_FMT,
)
from .exception import InputValueError, SuprsendAPIException, SuprsendValidationError
from .object_helper import _ObjectInternalHelper
from .signature import get_request_signature


class ObjectsApi:
    def __init__(self, config):
        self.config = config
        self.list_url = self.__list_url()
        self.__headers = self.__common_headers()

    def __list_url(self):
        list_uri_template = "{}v1/object/"
        list_uri_template = list_uri_template.format(self.config.base_url)
        return list_uri_template

    def __common_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.config.user_agent,
        }

    def __dynamic_headers(self):
        return {
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
        }

    def list(self, object_type: str, options: Dict = None):
        params = options or {}
        encoded_params = urllib.parse.urlencode(params)
        #
        object_type_encoded = urllib.parse.quote_plus(object_type)
        url = f"{self.list_url}{object_type_encoded}?{encoded_params}"
        # ---
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'GET', None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def _validate_object_type(self, object_type):
        if not isinstance(object_type, (str,)):
            raise SuprsendValidationError("object_type must be a string")
        object_type = object_type.strip()
        if not object_type:
            raise SuprsendValidationError("missing object_type")
        return object_type

    def _validate_object_id(self, object_id):
        if not isinstance(object_id, (str,)):
            raise SuprsendValidationError("object_id must be a string")
        object_id = object_id.strip()
        if not object_id:
            raise SuprsendValidationError("missing object_id")
        return object_id

    def detail_url(self, object_type: str, object_id: str):
        object_type_encoded = urllib.parse.quote_plus(object_type)
        object_id_encoded = urllib.parse.quote_plus(object_id)
        url = f"{self.list_url}{object_type_encoded}/{object_id_encoded}/"
        return url

    def get(self, object_type: str, object_id: str):
        url = self.detail_url(object_type, object_id)
        # ---
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'GET', None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def upsert(self, object_type: str, object_id: str, object_payload: Dict):
        url = self.detail_url(object_type, object_id)
        # ---
        object_payload = object_payload or {}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', object_payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def update(self, object_type: str, object_id: str, object_payload: Dict):
        url = self.detail_url(object_type, object_id)
        # ---
        object_payload = object_payload or {}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'PATCH', object_payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete(self, object_type: str, object_id: str):
        url = self.detail_url(object_type, object_id)
        # ---
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'DELETE', "", headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def bulk_delete(self, object_type: str, object_ids: list):
        object_type_encoded = urllib.parse.quote_plus(object_type)
        url = f"{self.list_url}{object_type_encoded}/"
        # ---
        payload = {
            "object_ids": object_ids
        }
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'DELETE', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def get_subscriptions(self, object_type: str, object_id: str):
        object_type = self._validate_object_type(object_type)
        object_id = self._validate_object_id(object_id)
        url = f"{self.detail_url(object_type, object_id)}subscription/"
        # ---
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'GET', None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def create_subscriptions(self, object_type: str, object_id: str, payload: Dict):
        object_type = self._validate_object_type(object_type)
        object_id = self._validate_object_id(object_id)
        url = f"{self.detail_url(object_type, object_id)}subscription/"
        # ---
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete_subscriptions(self, object_type: str, object_id: str, payload: Dict):
        object_type = self._validate_object_type(object_type)
        object_id = self._validate_object_id(object_id)
        url = f"{self.detail_url(object_type, object_id)}subscription/"
        # ---
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'DELETE', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def get_instance(self, object_type: str = None, object_id: str = None):
        if not isinstance(object_type, (str,)):
            raise InputValueError("object_type must be a string. an Id which uniquely identify a user in your app")
        object_type = object_type.strip()
        if not object_type:
            raise InputValueError("object_type must be passed")
        # ---
        if not isinstance(object_id, (str,)):
            raise InputValueError("object_id must be a string. an Id which uniquely identify a user in your app")
        object_id = object_id.strip()
        if not object_id:
            raise InputValueError("object_id must be passed")
        # -----
        return _Objects(self.config, object_type, object_id)


class _Objects:
    def __init__(self, config, object_type, object_id):
        self.config = config
        self.object_type = object_type
        self.object_id = object_id
        self.__url = self.__get_url()
        #
        self.operations = []
        self._helper = _ObjectInternalHelper()

    def __get_url(self):
        url_formatted = "{}v1/object/{}/{}/".format(self.config.base_url, self.object_type, self.object_id)
        return url_formatted

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
            "User-Agent": self.config.user_agent,
        }

    def __super_properties(self):
        return {
            "$ss_sdk_version": self.config.user_agent
        }

    def save(self):
        headers = self.__get_headers()
        payload = {
            "operations": self.operations
        }
        # --- Signature and Authorization-header
        content_txt, sig = get_request_signature(self.__url, 'PATCH', payload, headers,
                                                 self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(self.__url,
                              data=content_txt.encode('utf-8'),
                              headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def append(self, arg1, arg2=None):
        """
        Usage:
        1. append(k, v)
        2. append({k1: v1, k2, v2})

        :param arg1: one of [str, dict]
        :param arg2: required if arg1 is string
        :return:
        """
        caller = "append"
        if not isinstance(arg1, (str, dict)):
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                return
            else:
                self._helper._append_kv(arg1, arg2, {}, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)
        else:
            for k, v in arg1.items():
                self._helper._append_kv(k, v, arg1, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)

    def set(self, arg1, arg2=None):
        """
        1. set(k, v)
        2. set({k1: v1, k2, v2})

        :param arg1: required, one of  [str, dict]
        :param arg2: required if arg1 is str
        :return:
        """
        caller = "set"
        if not isinstance(arg1, (str, dict)):
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                return
            else:
                self._helper._set_kv(arg1, arg2, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)
        else:
            for k, v in arg1.items():
                self._helper._set_kv(k, v, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)

    def set_once(self, arg1, arg2=None):
        """
        1. set_once(k, v)
        2. set_once({k1: v1, k2, v2})

        :param arg1: required, one of  [str, dict]
        :param arg2: required if arg1 is str
        :return:
        """
        caller = "set_once"
        if not isinstance(arg1, (str, dict)):
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                return
            else:
                self._helper._set_once_kv(arg1, arg2, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)
        else:
            for k, v in arg1.items():
                self._helper._set_once_kv(k, v, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)

    def increment(self, arg1, arg2=None):
        """
        1. increment(k, v)
        2. increment({k1: v1, k2, v2})

        :param arg1: required, one of  [str, dict]
        :param arg2: required if arg1 is str
        :return:
        """
        caller = "increment"
        if not isinstance(arg1, (str, dict)):
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                return
            else:
                self._helper._increment_kv(arg1, arg2, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)
        else:
            for k, v in arg1.items():
                self._helper._increment_kv(k, v, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)

    def remove(self, arg1, arg2=None):
        """
        Usage:
        1. remove(k, v)
        2. remove({k1: v1, k2, v2})

        :param arg1: one of [str, dict]
        :param arg2: required if arg1 is string
        :return:
        """
        caller = "remove"
        if not isinstance(arg1, (str, dict)):
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                return
            else:
                self._helper._remove_kv(arg1, arg2, {}, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)
        else:
            for k, v in arg1.items():
                self._helper._remove_kv(k, v, arg1, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)

    def unset(self, key):
        """
        Usage:
        1. unset(k)
        2. unset([k1, k2])

        :param key: one of [str, list[str]]
        :return:
        """
        caller = "unset"
        if not isinstance(key, (str, list, tuple)):
            return
        if isinstance(key, (str,)):
            self._helper._unset_k(key, caller=caller)
            payload = self._helper.form_payload()
            self.operations.append(payload)
        else:
            for k in key:
                self._helper._unset_k(k, caller=caller)
                payload = self._helper.form_payload()
                self.operations.append(payload)

    # ------------------------ Preferred language
    def set_preferred_language(self, lang_code):
        """
        :param lang_code:
        :return:
        """
        caller = "set_preferred_language"
        self._helper._set_preferred_language(lang_code, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ Timezone
    def set_timezone(self, timezone):
        """
        :param timezone:
        :return:
        """
        caller = "set_timezone"
        self._helper._set_timezone(timezone, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ Email
    def add_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_email"
        self._helper._add_email(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_email"
        self._helper._remove_email(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ SMS
    def add_sms(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_sms"
        self._helper._add_sms(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_sms(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_sms"
        self._helper._remove_sms(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ Whatsapp
    def add_whatsapp(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_whatsapp"
        self._helper._add_whatsapp(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_whatsapp(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_whatsapp"
        self._helper._remove_whatsapp(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ Androidpush [providers: fcm / xiaomi / oppo]
    def add_androidpush(self, value: str, provider: str = "fcm"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_androidpush"
        self._helper._add_androidpush(value, provider, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_androidpush(self, value: str, provider: str = "fcm"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_androidpush"
        self._helper._remove_androidpush(value, provider, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ Iospush [providers: apns]
    def add_iospush(self, value: str, provider: str = "apns"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_iospush"
        self._helper._add_iospush(value, provider, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_iospush(self, value: str, provider: str = "apns"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_iospush"
        self._helper._remove_iospush(value, provider, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ Webpush [providers: vapid]
    def add_webpush(self, value: dict, provider: str = "vapid"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_webpush"
        self._helper._add_webpush(value, provider, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_webpush(self, value: dict, provider: str = "vapid"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_webpush"
        self._helper._remove_webpush(value, provider, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ Slack
    def add_slack(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "add_slack"
        self._helper._add_slack(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_slack(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "remove_slack"
        self._helper._remove_slack(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    # ------------------------ MS Teams
    def add_ms_teams(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "add_ms_teams"
        self._helper._add_ms_teams(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)

    def remove_ms_teams(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "remove_ms_teams"
        self._helper._remove_ms_teams(value, caller=caller)
        payload = self._helper.form_payload()
        self.operations.append(payload)
