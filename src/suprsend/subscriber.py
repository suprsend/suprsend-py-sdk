import json
import uuid
import time
from datetime import datetime, timezone
import requests

from .constants import (
    HEADER_DATE_FMT,
    IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES,
    IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
)
from .signature import get_request_signature
from .utils import (get_apparent_identity_event_size, )
from .subscriber_helper import _SubscriberInternalHelper


class SubscriberFactory:
    def __init__(self, config):
        self.config = config

    def new(self, distinct_id: str = None):
        return self.get_instance(distinct_id)

    def get_instance(self, distinct_id: str = None):
        if not isinstance(distinct_id, (str,)):
            raise ValueError("distinct_id must be a string. an Id which uniquely identify a user in your app")
        distinct_id = distinct_id.strip()
        if not distinct_id:
            raise ValueError("distinct_id must be passed")
        # -----
        return Subscriber(self.config, distinct_id)


class Subscriber:
    def __init__(self, config, distinct_id):
        self.config = config
        self.distinct_id = distinct_id
        self.__url = self.__get_url()
        self.__super_props = self.__super_properties()
        #
        self.__errors = []
        self.__info = []
        self._append_count = 0
        self._remove_count = 0
        self._set_count = 0
        self._unset_count = 0
        self._events = []
        self._helper = _SubscriberInternalHelper(distinct_id, config.workspace_key)

    def __get_url(self):
        url_template = "{}event/"
        if self.config.include_signature_param:
            if self.config.auth_enabled:
                url_template = url_template + "?verify=true"
            else:
                url_template = url_template + "?verify=false"
        url_formatted = url_template.format(self.config.base_url)
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

    @property
    def warnings(self):
        return self.__info

    @property
    def errors(self):
        return self.__errors

    def events(self):
        # Don't mutate the original array. Make a copy of _events
        all_events = [*self._events]
        for e in all_events:
            e["properties"] = self.__super_props
        # --------------------
        # Add $identify event by default, if new properties get added
        if len(all_events) == 0 or self._set_count > 0 or self._append_count > 0:
            user_identify_event = {
                "$insert_id": str(uuid.uuid4()),
                "$time": int(time.time() * 1000),
                "env": self.config.workspace_key,
                "event": "$identify",
                "properties": {
                    # Don't add $anon_id to properties,
                    **{"$identified_id": self.distinct_id},
                    **self.__super_props
                },
            }
            # Add $identify event at the 0th index, so that $identify runs before $append/$remove/$reset
            all_events.insert(0, user_identify_event)
        # ---------
        return all_events

    def validate_event_size(self, event_dict):
        apparent_size = get_apparent_identity_event_size(event_dict)
        if apparent_size > IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise ValueError(f"User Event size too big - {apparent_size} Bytes, "
                             f"must not cross {IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return event_dict, apparent_size

    def validate_body(self, is_part_of_bulk=False):
        warnings_list = []
        if self.__info:
            msg = f"[distinct_id: {self.distinct_id}]" + "\n".join(self.__info)
            warnings_list.append(msg)
            # print on console as well
            print(f"WARNING: {msg}")
        if self.__errors:
            msg = f"[distinct_id: {self.distinct_id}]" + "\n".join(self.__errors)
            warnings_list.append(msg)
            err_msg = f"ERROR: {msg}"
            if is_part_of_bulk:
                # print on console in case of bulk-api
                print(err_msg)
            else:
                # raise error in case of single api
                raise ValueError(err_msg)
        # ------
        return warnings_list

    def save(self):
        try:
            self.validate_body(is_part_of_bulk=False)
            headers = self.__get_headers()
            events = self.events()
            # --- validate event size
            for ev in events:
                ev, size = self.validate_event_size(ev)

            # --- Based on whether signature is required or not, add Authorization header
            if self.config.auth_enabled:
                # Signature and Authorization-header
                content_txt, sig = get_request_signature(self.__url, 'POST', events, headers,
                                                         self.config.workspace_secret)
                headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
            else:
                content_txt = json.dumps(events, ensure_ascii=False)
            # -----
            resp = requests.post(self.__url,
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

    def _collect_event(self, discard_if_error=False):
        resp = self._helper.get_identity_event()
        if resp["errors"]:
            self.__errors.extend(resp["errors"])
        if resp["info"]:
            self.__info.extend(resp["info"])

        if resp["event"]:
            self._events.append(resp["event"])
            self._set_count += resp["set"]
            self._append_count += resp["append"]
            self._remove_count += resp["remove"]
            self._unset_count += resp["unset"]

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
            self.__errors.append(f"[{caller}] arg1 must be either string or a dict")
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                self.__errors.append(f"[{caller}] if arg1 is a string, then arg2 must be passed")
                return
            else:
                self._helper._append_kv(arg1, arg2, {}, caller=caller)
                self._collect_event(discard_if_error=True)
        else:
            for k, v in arg1.items():
                self._helper._append_kv(k, v, arg1, caller=caller)
            # --
            self._collect_event(discard_if_error=False)

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
            self.__errors.append(f"[{caller}] arg1 must be either string or a dict")
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                self.__errors.append(f"[{caller}] if arg1 is a string, then arg2 must be passed")
                return
            else:
                self._helper._remove_kv(arg1, arg2, {}, caller=caller)
                self._collect_event(discard_if_error=True)
        else:
            for k, v in arg1.items():
                self._helper._remove_kv(k, v, arg1, caller=caller)
            # --
            self._collect_event(discard_if_error=False)

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
            self.__errors.append(f"[{caller}] key must be either String or List[string]")
            return
        if isinstance(key, (str,)):
            self._helper._unset_k(key, caller=caller)
            self._collect_event(discard_if_error=True)
        else:
            for k in key:
                self._helper._unset_k(k, caller=caller)
            # --
            self._collect_event(discard_if_error=False)

    # ------------------------ Preferred language
    def set_preferred_language(self, lang_code):
        """

        :param lang_code:
        :return:
        """
        caller = "set_preferred_language"
        self._helper._set_preferred_language(lang_code, caller=caller)
        self._collect_event(discard_if_error=True)

    # ------------------------ Email
    def add_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_email"
        self._helper._add_email(value, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_email"
        self._helper._remove_email(value, caller=caller)
        self._collect_event(discard_if_error=True)

    # ------------------------ SMS
    def add_sms(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_sms"
        self._helper._add_sms(value, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_sms(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_sms"
        self._helper._remove_sms(value, caller=caller)
        self._collect_event(discard_if_error=True)

    # ------------------------ Whatsapp
    def add_whatsapp(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_whatsapp"
        self._helper._add_whatsapp(value, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_whatsapp(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_whatsapp"
        self._helper._remove_whatsapp(value, caller=caller)
        self._collect_event(discard_if_error=True)

    # ------------------------ Androidpush [providers: fcm / xiaomi / oppo]
    def add_androidpush(self, value: str, provider: str = "fcm"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_androidpush"
        self._helper._add_androidpush(value, provider, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_androidpush(self, value: str, provider: str = "fcm"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_androidpush"
        self._helper._remove_androidpush(value, provider, caller=caller)
        self._collect_event(discard_if_error=True)

    # ------------------------ Iospush [providers: apns]
    def add_iospush(self, value: str, provider: str = "apns"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_iospush"
        self._helper._add_iospush(value, provider, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_iospush(self, value: str, provider: str = "apns"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_iospush"
        self._helper._remove_iospush(value, provider, caller=caller)
        self._collect_event(discard_if_error=True)

    # ------------------------ Webpush [providers: vapid]
    def add_webpush(self, value: dict, provider: str = "vapid"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_webpush"
        self._helper._add_webpush(value, provider, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_webpush(self, value: dict, provider: str = "vapid"):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_webpush"
        self._helper._remove_webpush(value, provider, caller=caller)
        self._collect_event(discard_if_error=True)

    # ------------------------ Slack
    def add_slack_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_slack_email"
        self._helper._add_slack({"email": value}, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_slack_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_slack_email"
        self._helper._remove_slack({"email": value}, caller=caller)
        self._collect_event(discard_if_error=True)

    def add_slack_userid(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_slack_userid"
        self._helper._add_slack({"user_id": value}, caller=caller)
        self._collect_event(discard_if_error=True)

    def remove_slack_userid(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_slack_userid"
        self._helper._remove_slack({"user_id": value}, caller=caller)
        self._collect_event(discard_if_error=True)
