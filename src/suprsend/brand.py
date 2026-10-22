from typing import List, Dict, TYPE_CHECKING

from .exception import SuprsendAPIException
from .utils import urlencode_query, urlencode_path_param

if TYPE_CHECKING:
    from .sdkinstance import Suprsend


class BrandsApi:
    def __init__(self, config: "Suprsend"):
        self.config = config
        self.list_url = self.__list_url()

    def __list_url(self):
        list_uri_template = "{}v1/brand/"
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

    def detail_url(self, brand_id: str):
        brand_id = str(brand_id).strip()
        brand_id_encoded = urlencode_path_param(brand_id)
        url = f"{self.list_url}{brand_id_encoded}/"
        return url

    def get(self, brand_id: str):
        url = self.detail_url(brand_id)
        # ---
        resp = self.config.request('GET', url, None)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def upsert(self, brand_id: str, brand_payload: Dict):
        url = self.detail_url(brand_id)
        # ---
        brand_payload = brand_payload or {}
        resp = self.config.request('POST', url, brand_payload)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()
