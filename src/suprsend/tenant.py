import requests
from typing import Dict
import urllib.parse

from .exception import SuprsendAPIException, SuprsendValidationError
from .signature import get_request_signature
from .utils import urlencode_query


class TenantsApi:
    def __init__(self, config):
        self.config = config
        self.list_url = self.__list_url()

    def __list_url(self):
        list_uri_template = "{}v1/tenant/"
        list_uri_template = list_uri_template.format(self.config.base_url)
        return list_uri_template

    def cleaned_limit_offset(self, limit: int, offset: int):
        # limit must be 0 < x <= 1000
        limit = limit if (isinstance(limit, int) and 0 < limit <= 1000) else 20
        # offset must be >=0
        offset = offset if (isinstance(offset, int) and offset >= 0) else 0
        #
        return limit, offset

    def list(self, limit: int = 20, offset: int = 0):
        limit, offset = self.cleaned_limit_offset(limit, offset)
        params = {"limit": limit, "offset": offset}
        encoded_params = urllib.parse.urlencode(params)
        #
        url = f"{self.list_url}?{encoded_params}"
        # ---
        headers = self.config.default_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'GET', None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def _validate_tenant_id(self, tenant_id):
        if not isinstance(tenant_id, (str,)):
            raise SuprsendValidationError("tenant_id must be a string")
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise SuprsendValidationError("missing tenant_id")
        return tenant_id

    def detail_url(self, tenant_id: str):
        tenant_id_encoded = urllib.parse.quote_plus(tenant_id)
        url = f"{self.list_url}{tenant_id_encoded}/"
        return url

    def get(self, tenant_id: str):
        tenant_id = self._validate_tenant_id(tenant_id)
        url = self.detail_url(tenant_id)
        # ---
        headers = self.config.default_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'GET', None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def upsert(self, tenant_id: str, tenant_payload: Dict):
        tenant_id = self._validate_tenant_id(tenant_id)
        url = self.detail_url(tenant_id)
        # ---
        tenant_payload = tenant_payload or {}
        headers = self.config.default_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', tenant_payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete(self, tenant_id: str):
        tenant_id = self._validate_tenant_id(tenant_id)
        url = self.detail_url(tenant_id)
        # ---
        headers = self.config.default_headers()
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'DELETE', "", headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.delete(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return {"success": True, "status_code": resp.status_code}

    def list_preference_categories(self, tenant_id: str, options: Dict = None) -> Dict:
        """
        GET /v1/tenant/{tenant_id}/preference/category/ - returns all category preferences for a tenant.
        options: {"limit": 10, "offset": 0, tags: "", "locale": "", "include_disabled": false}
        """
        tenant_id = self._validate_tenant_id(tenant_id)
        encoded_options = urlencode_query(options or {})
        url = "{}preference/category/{}".format(self.detail_url(tenant_id), (f"?{encoded_options}" if encoded_options else ""))
        # -----
        headers = self.config.default_headers()
        content_txt, sig = get_request_signature(url, 'GET', None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def get_preference_category(self, tenant_id: str, category: str, options: Dict = None) -> Dict:
        """
        GET /v1/tenant/{tenant_id}/preference/category/{category}/?locale=xx
        options: {"locale": ""}
        """
        tenant_id = self._validate_tenant_id(tenant_id)
        category_encoded = urllib.parse.quote_plus(category)
        encoded_options = urlencode_query(options or {})
        url = "{}preference/category/{}/{}".format(self.detail_url(tenant_id), category_encoded, (f"?{encoded_options}" if encoded_options else ""))
        # -----
        headers = self.config.default_headers()
        content_txt, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def update_preference_category(self, tenant_id: str, category: str, payload: Dict, options: Dict = None) -> Dict:
        """
        PATCH /v1/tenant/{tenant_id}/preference/category/{category}/?locale=xx
        options: {"locale": ""}
        payload: {
            "enabled_for_tenant": true,
            "blocked_channels": [],
            "visible_to_subscriber": null/bool,
            "preference": "",
            "mandatory_channels": [],
            "opt_in_channels": [],
            "digest_schedule": null,
            "properties": null/[],
        }
        """
        tenant_id = self._validate_tenant_id(tenant_id)
        category_encoded = urllib.parse.quote_plus(category)
        encoded_options = urlencode_query(options or {})
        url = "{}preference/category/{}/{}".format(self.detail_url(tenant_id), category_encoded, (f"?{encoded_options}" if encoded_options else ""))
        # -----
        payload = payload or {}
        headers = self.config.default_headers()
        content_txt, sig = get_request_signature(url, "PATCH", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.patch(url, data=content_txt.encode("utf-8"), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()
