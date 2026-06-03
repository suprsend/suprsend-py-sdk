import requests
import urllib.parse
from typing import Dict, List

from .exception import SuprsendAPIException
from .signature import get_request_signature


class SubscriberSyncApi:
    def __init__(self, config):
        self.config = config

    def _get(self, url: str, params: Dict = None) -> Dict:
        if params:
            encoded = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if encoded:
                url = f"{url}?{encoded}"
        headers = self.config.default_headers()
        _, sig = get_request_signature(url, "GET", None, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        resp = requests.get(url, headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def _post(self, url: str, payload: Dict) -> Dict:
        headers = self.config.default_headers()
        content_txt, sig = get_request_signature(url, "POST", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        resp = requests.post(url, data=content_txt.encode("utf-8"), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    def _patch(self, url: str, payload: Dict) -> Dict:
        headers = self.config.default_headers()
        content_txt, sig = get_request_signature(url, "PATCH", payload, headers, self.config.workspace_secret)
        headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
        resp = requests.patch(url, data=content_txt.encode("utf-8"), headers=headers)
        if resp.status_code >= 400:
            raise SuprsendAPIException(resp)
        return resp.json()

    # ── Schema ────────────────────────────────────────────────────────────────

    def get_schema(self) -> Dict:
        url = "{}v1/subscriber_sync_task/schema/".format(self.config.base_url)
        return self._get(url)

    # ── Subscriber list ───────────────────────────────────────────────────────

    def create_list(
        self,
        list_id: str,
        list_name: str,
        list_description: str = "",
        track_user_entry: bool = False,
        track_user_exit: bool = False,
    ) -> Dict:
        url = "{}v1/client_subscriber_list/".format(self.config.base_url)
        payload: Dict = {
            "list_id": list_id,
            "list_name": list_name,
            "list_type": "dynamic_list",
            "track_user_entry": track_user_entry,
            "track_user_exit": track_user_exit,
        }
        if list_description:
            payload["list_description"] = list_description
        return self._post(url, payload)

    def list_lists(
        self,
        list_type: str = "dynamic_list",
        limit: int = 20,
        offset: int = 0,
        list_id: str = "",
    ) -> Dict:
        url = "{}v1/client_subscriber_list/".format(self.config.base_url)
        params: Dict = {"list_type": list_type, "limit": limit, "offset": offset}
        if list_id:
            params["list_id"] = list_id
        return self._get(url, params=params)

    def get_list_subscribers(self, list_id: str, limit: int = 20) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_list/{}/subscriber/".format(self.config.base_url, encoded_id)
        return self._get(url, params={"limit": limit})

    # ── Sync task lifecycle ───────────────────────────────────────────────────

    def create_sync_task(self, name: str, list_id: str) -> Dict:
        url = "{}v1/subscriber_sync_task/".format(self.config.base_url)
        return self._post(url, {"name": name, "list_id": list_id})

    def get_task(self, list_id: str) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/".format(self.config.base_url, encoded_id)
        return self._get(url)

    def toggle_task(self, list_id: str, is_enabled: bool) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/".format(self.config.base_url, encoded_id)
        return self._patch(url, {"is_enabled": is_enabled})

    # ── Task version ─────────────────────────────────────────────────────────

    def get_task_draft(self, list_id: str) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/version/_/".format(self.config.base_url, encoded_id)
        return self._get(url)

    def get_task_active_version(self, list_id: str) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/version/active/".format(self.config.base_url, encoded_id)
        return self._get(url)

    def update_task_draft(
        self,
        list_id: str,
        query_text: str,
        update_type: str = "replace",
        column_mappings: List = None,
    ) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/version/_/".format(self.config.base_url, encoded_id)
        return self._patch(url, {
            "query_text": query_text,
            "update_type": update_type,
            "column_mappings": column_mappings or [],
        })

    def publish_task(
        self,
        list_id: str,
        query_text: str,
        update_type: str = "replace",
        column_mappings: List = None,
    ) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/version/_/".format(self.config.base_url, encoded_id)
        return self._patch(url, {
            "query_text": query_text,
            "update_type": update_type,
            "column_mappings": column_mappings or [],
            "status": "active",
        })

    # ── Dry run ───────────────────────────────────────────────────────────────

    def dry_run(self, list_id: str, query_text: str) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/version/_/dry_run/".format(self.config.base_url, encoded_id)
        return self._post(url, {"query_text": query_text})

    def dry_run_count(self, list_id: str, query_text: str) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/version/_/dry_run/count/".format(self.config.base_url, encoded_id)
        return self._post(url, {"query_text": query_text})

    # ── Execution ─────────────────────────────────────────────────────────────

    def run_now(self, list_id: str) -> Dict:
        encoded_id = urllib.parse.quote_plus(list_id)
        url = "{}v1/subscriber_sync_task/{}/schedule_now/".format(self.config.base_url, encoded_id)
        return self._post(url, {})

    def get_task_executions(self, list_id: str, limit: int = 10) -> Dict:
        url = "{}v1/task_request/".format(self.config.base_url)
        return self._get(url, params={"list_id": list_id, "limit": limit})
