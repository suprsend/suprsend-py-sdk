from datetime import datetime, timezone
import requests
import time
from typing import List, Dict
import urllib.parse
import uuid

from .exception import InputValueError, SuprsendAPIException, SuprsendValidationError
from .constants import (
    HEADER_DATE_FMT,
    SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES, SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
)
from .utils import (get_apparent_list_broadcast_body_size, validate_list_broadcast_body_schema)
from .signature import get_request_signature
from .attachment import get_attachment_json


class SubscriberListBroadcast:
    def __init__(self, body, idempotency_key: str = None, brand_id: str = None):
        if not isinstance(body, (dict,)):
            raise InputValueError("broadcast body must be a json/dictionary")
        self.body = body
        self.idempotency_key = idempotency_key
        self.brand_id = brand_id

    def add_attachment(self, file_path: str, file_name: str = None, ignore_if_error: bool = False):
        if self.body.get("data") is None:
            self.body["data"] = {}
        # if body["data"] is not a dict, not raising error while adding attachment.
        if not isinstance(self.body["data"], (dict,)):
            print("WARNING: attachment cannot be added. please make sure body['data'] is a dictionary. "
                  "SubscriberListBroadcast" + str(self.as_json()))
            return
        # ---
        attachment = get_attachment_json(file_path, file_name, ignore_if_error)
        if not attachment:
            return
        # --- add the attachment to body->data->$attachments
        if self.body["data"].get("$attachments") is None:
            self.body["data"]["$attachments"] = []
        # -----
        self.body["data"]["$attachments"].append(attachment)

    def get_final_json(self):
        self.body["$insert_id"] = str(uuid.uuid4())
        self.body["$time"] = int(time.time() * 1000)
        if self.idempotency_key:
            self.body["$idempotency_key"] = self.idempotency_key
        if self.brand_id:
            self.body["brand_id"] = self.brand_id
        # --
        self.body = validate_list_broadcast_body_schema(self.body)
        # ---- Check body size
        apparent_size = get_apparent_list_broadcast_body_size(self.body)
        if apparent_size > SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise InputValueError(f"SubscriberListBroadcast body too big - {apparent_size} Bytes, "
                                  f"must not cross {SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return self.body, apparent_size

    def as_json(self):
        body_dict = {**self.body}
        if self.idempotency_key:
            body_dict["$idempotency_key"] = self.idempotency_key
        if self.brand_id:
            body_dict["brand_id"] = self.brand_id
        # -----
        return body_dict


class SubscriberListsApi:
    def __init__(self, config):
        self.config = config
        self.subscriber_list_url = "{}v1/subscriber_list/".format(self.config.base_url)
        self.broadcast_url = "{}{}/broadcast/".format(self.config.base_url, self.config.workspace_key)
        self.__headers = self.__common_headers()
        self.non_error_default_response = {"success": True}

    def __common_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.config.user_agent,
        }

    def __dynamic_headers(self):
        return {
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
        }

    def _validate_list_id(self, list_id):
        if not isinstance(list_id, (str,)):
            raise SuprsendValidationError("list_id must be a string")
        list_id = list_id.strip()
        if not list_id:
            raise SuprsendValidationError("missing list_id")
        return list_id

    def create(self, payload: Dict):
        if not payload:
            raise SuprsendValidationError("missing payload")
        list_id = payload.get("list_id")
        if not list_id:
            raise SuprsendValidationError("missing list_id is payload")
        list_id = self._validate_list_id(list_id)
        # -----
        payload["list_id"] = list_id
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(self.subscriber_list_url, 'POST', payload, headers,
                                                 self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(self.subscriber_list_url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def cleaned_limit_offset(self, limit: int, offset: int):
        # limit must be 0 < x <= 1000
        limit = limit if (isinstance(limit, int) and 0 < limit <= 1000) else 20
        # offset must be >=0
        offset = offset if (isinstance(offset, int) and offset >= 0) else 0
        #
        return limit, offset

    def get_all(self, limit: int = 20, offset: int = 0):
        limit, offset = self.cleaned_limit_offset(limit, offset)
        params = {"limit": limit, "offset": offset}
        encoded_params = urllib.parse.urlencode(params)
        #
        url = f"{self.subscriber_list_url}?{encoded_params}"
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

    def __subscriber_list_detail_url(self, list_id: str):
        list_id = str(list_id).strip()
        list_id_encoded = urllib.parse.quote_plus(list_id)
        url = f"{self.subscriber_list_url}{list_id_encoded}/"
        return url

    def get(self, list_id: str):
        list_id = self._validate_list_id(list_id)
        # --------
        url = self.__subscriber_list_detail_url(list_id)
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

    def add(self, list_id: str, distinct_ids: list):
        list_id = self._validate_list_id(list_id)
        if not isinstance(distinct_ids, (list, )):
            raise SuprsendValidationError("distinct_ids must be list of strings")
        if len(distinct_ids) == 0:
            return self.non_error_default_response
        url = "{}subscriber/add/".format(self.__subscriber_list_detail_url(list_id))
        payload = {"distinct_ids": distinct_ids}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def remove(self, list_id: str, distinct_ids: list):
        list_id = self._validate_list_id(list_id)
        if not isinstance(distinct_ids, (list,)):
            raise SuprsendValidationError("distinct_ids must be list of strings")
        if len(distinct_ids) == 0:
            return self.non_error_default_response
        url = "{}subscriber/remove/".format(self.__subscriber_list_detail_url(list_id))
        payload = {"distinct_ids": distinct_ids}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete(self, list_id: str):
        list_id = self._validate_list_id(list_id)
        url = "{}delete/".format(self.__subscriber_list_detail_url(list_id))
        headers = {**self.__headers, **self.__dynamic_headers()}
        payload = {}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'PATCH', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def broadcast(self, broadcast_instance: SubscriberListBroadcast) -> Dict:
        if not isinstance(broadcast_instance, SubscriberListBroadcast):
            raise InputValueError("argument must be an instance of suprsend.SubscriberListBroadcast")

        broadcast_body, body_size = broadcast_instance.get_final_json()
        try:
            headers = {**self.__headers, **self.__dynamic_headers()}
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(self.broadcast_url, 'POST', broadcast_body,
                                                     headers, self.config.workspace_secret)
            headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
            # -----
            resp = requests.post(self.broadcast_url,
                                 data=content_txt.encode('utf-8'),
                                 headers=headers)
        except Exception as ex:
            error_str = ex.__str__()
            return {
                "success": False,
                "status": "fail",
                "status_code": 500,
                "message": error_str,
            }
        else:
            ok_response = resp.status_code // 100 == 2
            if ok_response:
                return {
                    "success": True,
                    "status": "success",
                    "status_code": resp.status_code,
                    "message": resp.text,
                }
            else:
                return {
                    "success": False,
                    "status": "fail",
                    "status_code": resp.status_code,
                    "message": resp.text,
                }

    def start_sync(self, list_id: str):
        list_id = self._validate_list_id(list_id)

        url = "{}start_sync/".format(self.__subscriber_list_detail_url(list_id))
        payload = {}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def _validate_version_id(self, version_id):
        if not isinstance(version_id, (str,)):
            raise SuprsendValidationError("version_id must be a string")
        version_id = version_id.strip()
        if not version_id:
            raise SuprsendValidationError("missing version_id")
        return version_id

    def __subscriber_list_url_with_version(self, list_id: str, version_id: str):
        list_id = str(list_id).strip()
        list_id_encoded = urllib.parse.quote_plus(list_id)
        version_id = str(version_id).strip()
        version_id_encoded = urllib.parse.quote_plus(version_id)
        url = f"{self.subscriber_list_url}{list_id_encoded}/version/{version_id_encoded}/"
        return url

    def get_version(self, list_id: str, version_id: str):
        list_id = self._validate_list_id(list_id)
        version_id = self._validate_version_id(version_id)
        # --------
        url = self.__subscriber_list_url_with_version(list_id, version_id)
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

    def add_to_version(self, list_id: str, version_id: str, distinct_ids: list):
        list_id = self._validate_list_id(list_id)
        if not isinstance(distinct_ids, (list,)):
            raise SuprsendValidationError("distinct_ids must be list of strings")
        if len(distinct_ids) == 0:
            return self.non_error_default_response

        version_id = self._validate_version_id(version_id)
        url = "{}subscriber/add/".format(self.__subscriber_list_url_with_version(list_id, version_id))
        payload = {"distinct_ids": distinct_ids}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def remove_from_version(self, list_id: str, version_id: str, distinct_ids: list):
        list_id = self._validate_list_id(list_id)
        if not isinstance(distinct_ids, (list,)):
            raise SuprsendValidationError("distinct_ids must be list of strings")
        if len(distinct_ids) == 0:
            return self.non_error_default_response
        version_id = self._validate_version_id(version_id)
        url = "{}subscriber/remove/".format(self.__subscriber_list_url_with_version(list_id, version_id))
        payload = {"distinct_ids": distinct_ids}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def finish_sync(self, list_id: str, version_id: str):
        list_id = self._validate_list_id(list_id)
        version_id = self._validate_version_id(version_id)
        url = "{}finish_sync/".format(self.__subscriber_list_url_with_version(list_id, version_id))
        payload = {}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'PATCH', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete_version(self, list_id: str, version_id: str):
        list_id = self._validate_list_id(list_id)
        version_id = self._validate_version_id(version_id)

        url = "{}delete/".format(self.__subscriber_list_url_with_version(list_id, version_id))
        headers = {**self.__headers, **self.__dynamic_headers()}
        payload = {}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'PATCH', payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()
