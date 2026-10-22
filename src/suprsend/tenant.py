from typing import Dict, TYPE_CHECKING

from .exception import SuprsendAPIException, SuprsendValidationError
from .utils import urlencode_query, urlencode_path_param

if TYPE_CHECKING:
    from .sdkinstance import Suprsend


class TenantsApi:
    def __init__(self, config: "Suprsend"):
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
        encoded_params = urlencode_query(params)
        #
        url = f"{self.list_url}?{encoded_params}"
        # ---
        resp = self.config.request('GET', url, None)
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
        tenant_id_encoded = urlencode_path_param(tenant_id)
        url = f"{self.list_url}{tenant_id_encoded}/"
        return url

    def get(self, tenant_id: str):
        tenant_id = self._validate_tenant_id(tenant_id)
        url = self.detail_url(tenant_id)
        # ---
        resp = self.config.request('GET', url, None)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def upsert(self, tenant_id: str, tenant_payload: Dict):
        tenant_id = self._validate_tenant_id(tenant_id)
        url = self.detail_url(tenant_id)
        # ---
        tenant_payload = tenant_payload or {}
        resp = self.config.request('POST', url, tenant_payload)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def delete(self, tenant_id: str):
        tenant_id = self._validate_tenant_id(tenant_id)
        url = self.detail_url(tenant_id)
        # ---
        resp = self.config.request('DELETE', url, "")
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
        resp = self.config.request('GET', url, None)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def get_preference_category(self, tenant_id: str, category: str, options: Dict = None) -> Dict:
        """
        GET /v1/tenant/{tenant_id}/preference/category/{category}/?locale=xx
        options: {"locale": ""}
        """
        tenant_id = self._validate_tenant_id(tenant_id)
        category_encoded = urlencode_path_param(category)
        encoded_options = urlencode_query(options or {})
        url = "{}preference/category/{}/{}".format(self.detail_url(tenant_id), category_encoded, (f"?{encoded_options}" if encoded_options else ""))
        # -----
        resp = self.config.request("GET", url, None)
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
        category_encoded = urlencode_path_param(category)
        encoded_options = urlencode_query(options or {})
        url = "{}preference/category/{}/{}".format(self.detail_url(tenant_id), category_encoded, (f"?{encoded_options}" if encoded_options else ""))
        # -----
        payload = payload or {}
        resp = self.config.request("PATCH", url, payload)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()
