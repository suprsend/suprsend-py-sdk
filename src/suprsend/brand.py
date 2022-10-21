from datetime import datetime, timezone
import requests
from typing import List, Dict
import urllib.parse

from .exception import SuprsendAPIException
from .constants import HEADER_DATE_FMT
from .signature import get_request_signature


class BrandsApi:
    def __init__(self, config):
        self.config = config
        self.list_url = self.__list_url()
        self.__headers = self.__common_headers()

    def __list_url(self):
        list_uri_template = "{}v1/brand/"
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
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'GET', None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def detail_url(self, brand_id: str):
        brand_id = str(brand_id).strip()
        brand_id_encoded = urllib.parse.quote_plus(brand_id)
        url = f"{self.list_url}{brand_id_encoded}/"
        return url

    def get(self, brand_id: str):
        url = self.detail_url(brand_id)
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

    def upsert(self, brand_id: str, brand_payload: Dict):
        url = self.detail_url(brand_id)
        # ---
        brand_payload = brand_payload or {}
        headers = {**self.__headers, **self.__dynamic_headers()}
        # Signature and Authorization-header
        content_txt, sig = get_request_signature(url, 'POST', brand_payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        # -----
        resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()
