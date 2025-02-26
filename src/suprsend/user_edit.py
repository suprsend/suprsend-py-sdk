from typing import Any, Dict, Iterable, Union
import time
import uuid

from .constants import (
    IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES,
    IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE,
)
from .exception import InputValueError
from .utils import (get_apparent_identity_event_size, )
from .user_edit_internal_helper import _UserEditInternalHelper


class UserEdit:
    def __init__(self, config, distinct_id: str):
        self.config = config
        self.distinct_id = distinct_id
        #
        self.__errors = []
        self.__info = []
        #
        self.operations = []
        self._helper = _UserEditInternalHelper()
        #
        self.__warnings_list = []

    @property
    def warnings(self):
        return self.__info

    @property
    def errors(self):
        return self.__errors

    def get_payload(self):
        return {"operations": self.operations}

    def get_async_payload(self):
        return {
            "$schema": "2",
            "$insert_id": str(uuid.uuid4()),
            "$time": int(time.time() * 1000),
            "env": self.config.workspace_key,
            "distinct_id": self.distinct_id,
            "$user_operations": self.operations,
            "properties": {"$ss_sdk_version": self.config.user_agent},
        }

    def as_json_async(self):
        return {
            "distinct_id": self.distinct_id,
            "$user_operations": self.operations,
            "warnings": self.__warnings_list,
        }

    def validate_payload_size(self, payload: Dict):
        apparent_size = get_apparent_identity_event_size(payload)
        if apparent_size > IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES:
            raise InputValueError(f"User Payload size too big - {apparent_size} Bytes, "
                                  f"must not cross {IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE}")
        # ----
        return payload, apparent_size

    def validate_body(self):
        self.__warnings_list = []
        if self.__info:
            msg = f"[distinct_id: {self.distinct_id}]" + "\n".join(self.__info)
            self.__warnings_list.append(msg)
            # print on console as well
            print(f"WARNING: {msg}")
        if self.__errors:
            msg = f"[distinct_id: {self.distinct_id}]" + "\n".join(self.__errors)
            self.__warnings_list.append(msg)
            print(f"ERROR: {msg}")
        # ------
        return self.__warnings_list

    def _collect_operation(self):
        resp = self._helper.get_operation_result()
        if resp["errors"]:
            self.__errors.extend(resp["errors"])
        if resp["info"]:
            self.__info.extend(resp["info"])
        if resp["operation"]:
            self.operations.append(resp["operation"])

    def append(self, arg1: Union[str, Dict], arg2: Any = None):
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
                self._collect_operation()
        else:
            for k, v in arg1.items():
                self._helper._append_kv(k, v, arg1, caller=caller)
            # --
            self._collect_operation()

    def set(self, arg1: Union[str, Dict], arg2: Any = None):
        """
        1. set(k, v)
        2. set({k1: v1, k2, v2})

        :param arg1: required, one of  [str, dict]
        :param arg2: required if arg1 is str
        :return:
        """
        caller = "set"
        if not isinstance(arg1, (str, dict)):
            self.__errors.append(f"[{caller}] arg1 must be String or a dict")
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                self.__errors.append(f"[{caller}] if arg1 is a string, then arg2 must be passed")
                return
            else:
                self._helper._set_kv(arg1, arg2, caller=caller)
                self._collect_operation()
        else:
            for k, v in arg1.items():
                self._helper._set_kv(k, v, caller=caller)
            # --
            self._collect_operation()

    def set_once(self, arg1: Union[str, Dict], arg2: Any = None):
        """
        1. set_once(k, v)
        2. set_once({k1: v1, k2, v2})

        :param arg1: required, one of  [str, dict]
        :param arg2: required if arg1 is str
        :return:
        """
        caller = "set_once"
        if not isinstance(arg1, (str, dict)):
            self.__errors.append(f"[{caller}] arg1 must be String or a dict")
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                self.__errors.append(f"[{caller}] if arg1 is a string, then arg2 must be passed")
                return
            else:
                self._helper._set_once_kv(arg1, arg2, caller=caller)
                self._collect_operation()
        else:
            for k, v in arg1.items():
                self._helper._set_once_kv(k, v, caller=caller)
            # --
            self._collect_operation()

    def increment(self, arg1: Union[str, Dict], arg2: Any = None):
        """
        1. increment(k, v)
        2. increment({k1: v1, k2, v2})

        :param arg1: required, one of  [str, dict]
        :param arg2: required if arg1 is str
        :return:
        """
        caller = "increment"
        if not isinstance(arg1, (str, dict)):
            self.__errors.append(f"[{caller}] arg1 must be String or a dict")
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                self.__errors.append(f"[{caller}] if arg1 is a string, then arg2 must be passed")
                return
            else:
                self._helper._increment_kv(arg1, arg2, caller=caller)
                self._collect_operation()
        else:
            for k, v in arg1.items():
                self._helper._increment_kv(k, v, caller=caller)
            # --
            self._collect_operation()

    def remove(self, arg1: Union[str, Dict], arg2: Any = None):
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
                self._collect_operation()
        else:
            for k, v in arg1.items():
                self._helper._remove_kv(k, v, arg1, caller=caller)
            # --
            self._collect_operation()

    def unset(self, key: Union[str, Iterable[str]]):
        """
        Usage:
        1. unset(k)
        2. unset([k1, k2])

        :param key: one of [str, list[str]]
        :return:
        """
        caller = "unset"
        if not isinstance(key, (str, list, tuple, set)):
            self.__errors.append(f"[{caller}] key must be either String or List[string]")
            return
        if isinstance(key, (str,)):
            self._helper._unset_k(key, caller=caller)
            self._collect_operation()
        else:
            for k in key:
                self._helper._unset_k(k, caller=caller)
            # --
            self._collect_operation()

    # ------------------------ Preferred language
    def set_preferred_language(self, lang_code: str):
        """
        :param lang_code:
        :return:
        """
        caller = "set_preferred_language"
        self._helper._set_preferred_language(lang_code, caller=caller)
        self._collect_operation()

    # ------------------------ Timezone
    def set_timezone(self, timezone: str):
        """
        :param timezone:
        :return:
        """
        caller = "set_timezone"
        self._helper._set_timezone(timezone, caller=caller)
        self._collect_operation()

    # ------------------------ Email
    def add_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_email"
        self._helper._add_email(value, caller=caller)
        self._collect_operation()

    def remove_email(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_email"
        self._helper._remove_email(value, caller=caller)
        self._collect_operation()

    # ------------------------ SMS
    def add_sms(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_sms"
        self._helper._add_sms(value, caller=caller)
        self._collect_operation()

    def remove_sms(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_sms"
        self._helper._remove_sms(value, caller=caller)
        self._collect_operation()

    # ------------------------ Whatsapp
    def add_whatsapp(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "add_whatsapp"
        self._helper._add_whatsapp(value, caller=caller)
        self._collect_operation()

    def remove_whatsapp(self, value: str):
        """

        :param value:
        :return:
        """
        caller = "remove_whatsapp"
        self._helper._remove_whatsapp(value, caller=caller)
        self._collect_operation()

    # ------------------------ Androidpush
    def add_androidpush(self, value: str, provider: str = None):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_androidpush"
        self._helper._add_androidpush(value, provider, caller=caller)
        self._collect_operation()

    def remove_androidpush(self, value: str, provider: str = None):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_androidpush"
        self._helper._remove_androidpush(value, provider, caller=caller)
        self._collect_operation()

    # ------------------------ Iospush [providers: apns]
    def add_iospush(self, value: str, provider: str = None):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_iospush"
        self._helper._add_iospush(value, provider, caller=caller)
        self._collect_operation()

    def remove_iospush(self, value: str, provider: str = None):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_iospush"
        self._helper._remove_iospush(value, provider, caller=caller)
        self._collect_operation()

    # ------------------------ Webpush [providers: vapid]
    def add_webpush(self, value: dict, provider: str = None):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "add_webpush"
        self._helper._add_webpush(value, provider, caller=caller)
        self._collect_operation()

    def remove_webpush(self, value: dict, provider: str = None):
        """

        :param value:
        :param provider:
        :return:
        """
        caller = "remove_webpush"
        self._helper._remove_webpush(value, provider, caller=caller)
        self._collect_operation()

    # ------------------------ Slack
    def add_slack(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "add_slack"
        self._helper._add_slack(value, caller=caller)
        self._collect_operation()

    def remove_slack(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "remove_slack"
        self._helper._remove_slack(value, caller=caller)
        self._collect_operation()

    # ------------------------ MS Teams
    def add_ms_teams(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "add_ms_teams"
        self._helper._add_ms_teams(value, caller=caller)
        self._collect_operation()

    def remove_ms_teams(self, value: dict):
        """

        :param value:
        :return:
        """
        caller = "remove_ms_teams"
        self._helper._remove_ms_teams(value, caller=caller)
        self._collect_operation()
