import json
import uuid
import time
import re
from datetime import datetime, timezone
import requests

from .constants import (HEADER_DATE_FMT, )
from .signature import get_request_signature


# ---------- Identity keys
IDENT_KEY_EMAIL="$email"
IDENT_KEY_SMS="$sms"
IDENT_KEY_ANDROIDPUSH="$androidpush"
IDENT_KEY_IOSPUSH="$iospush"
IDENT_KEY_WHATSAPP="$whatsapp"
IDENT_KEY_WEBPUSH="$webpush"

IDENT_KEYS_ALL = [IDENT_KEY_EMAIL, IDENT_KEY_SMS, IDENT_KEY_ANDROIDPUSH, IDENT_KEY_IOSPUSH,
                  IDENT_KEY_WHATSAPP, IDENT_KEY_WEBPUSH,]

OTHER_RESERVED_KEYS = [
    "$messenger", "$inbox",
    "$pushvendor", "$device_id",
    "$insert_id", "$time",
    "$set", "$set_once", "$add", "$append", "$remove", "$unset",
    "$identify", "$anon_id", "$identified_id",
    "$notification_delivered", "$notification_dismiss", "$notification_clicked",
]

SUPER_PROPERTY_KEYS = [
    "$app_version_string", "$app_build_number", "$brand", "$carrier", "$manufacturer", "$model", "$os",
    "$ss_sdk_version", "$insert_id", "$time"
]

ALL_RESERVED_KEYS = SUPER_PROPERTY_KEYS + OTHER_RESERVED_KEYS + IDENT_KEYS_ALL

# ---------
MOBILE_REGEX = r'^\+[0-9\s]+'
mobile_regex_compiled = re.compile(MOBILE_REGEX)

EMAIL_REGEX = r'^\S+@\S+\.\S+$'
email_regex_compiled = re.compile(EMAIL_REGEX)
# ---------


class IdentityFactory:
    def __init__(self, config):
        self.config = config

    def new(self, distinct_id: str = None):
        if not isinstance(distinct_id, (str,)):
            raise ValueError("distinct_id must be a string. an Id which uniquely identify a user in your app")
        distinct_id = distinct_id.strip()
        if not distinct_id:
            raise ValueError("distinct_id must be passed")
        # -----
        return IdentityEventTrigger(self.config, distinct_id)


class IdentityEventTrigger:
    def __init__(self, config, distinct_id):
        self.__config = config
        self.__url = self.__get_url()
        #
        self.__distinct_id = distinct_id
        #
        self.__dict_append = {}
        self.__dict_remove = {}
        self.__list_unset = []
        self.__errors = []

    def __get_url(self):
        url_template = "{}event/"
        if self.__config.include_signature_param:
            if self.__config.auth_enabled:
                url_template = url_template + "?verify=true"
            else:
                url_template = url_template + "?verify=false"
        url_formatted = url_template.format(self.__config.base_url)
        return url_formatted

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
            "User-Agent": self.__config.user_agent,
        }

    @property
    def errors(self):
        return self.__errors

    @property
    def events(self):
        all_events = []
        # -------------------- Modify Identity properties
        if (self.__dict_append or self.__dict_remove or self.__list_unset):
            user_properties_event = {
                "$insert_id": str(uuid.uuid4()),
                "$time": int(time.time() * 1000),
                "env": self.__config.workspace_key,
                "distinct_id": self.__distinct_id,
            }
            if self.__dict_append:
                user_properties_event["$append"] = self.__dict_append
            if self.__dict_remove:
                user_properties_event["$remove"] = self.__dict_remove
            if self.__list_unset:
                user_properties_event["$unset"] = self.__list_unset
            # ----
            all_events.append(user_properties_event)
        # --------------------
        # Add $identify event by default, if new properties get added
        if self.__dict_append:
            user_identify_event = {
                "$insert_id": str(uuid.uuid4()),
                "$time": int(time.time() * 1000),
                "env": self.__config.workspace_key,
                "event": "$identify",
                "properties": {
                    "$anon_id": self.__distinct_id,
                    "$identified_id": self.__distinct_id,
                },
            }
            all_events.append(user_identify_event)
        # ---------
        return all_events

    def __validate_body(self):
        if self.__errors:
            raise ValueError("\n".join(self.__errors))
        if not (self.__dict_append or self.__dict_remove or self.__list_unset):
            raise ValueError("no user properties have been edited. "
                             "Use user.append/remove/unset method to update user properties")

    def save(self):
        try:
            self.__validate_body()
            headers = self.__get_headers()
            events = self.events
            # Based on whether signature is required or not, add Authorization header
            if self.__config.auth_enabled:
                # Signature and Authorization-header
                # url: str, http_verb: str, content, headers: Dict, secret: str
                content_txt, sig = get_request_signature(self.__url, 'POST', events, headers,
                                                         self.__config.workspace_secret)
                headers["Authorization"] = "{}:{}".format(self.__config.workspace_key, sig)
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

    def append(self, arg1, arg2=None):
        """
        Usage:
        1. append(k, v)
        2. append({k1: v1, k2, v2})

        :param arg1: one of [str, dict]
        :param arg2: required if arg1 is string
        :return:
        """
        if not isinstance(arg1, (str, dict)):
            self.__errors.append("[append] arg1 must be either string or a dict")
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                self.__errors.append("[append] if arg1 is a string, then arg2 must be passed")
                return
            else:
                self.__append_kv(arg1, arg2, {})
        else:
            for k, v in arg1.items():
                self.__append_kv(k, v, arg1)

    def remove(self, arg1, arg2=None):
        """
        Usage:
        1. remove(k, v)
        2. remove({k1: v1, k2, v2})

        :param arg1: one of [str, dict]
        :param arg2: required if arg1 is string
        :return:
        """
        if not isinstance(arg1, (str, dict)):
            self.__errors.append("[remove] arg1 must be either string or a dict")
            return
        if isinstance(arg1, (str,)):
            if arg2 is None:
                self.__errors.append("[remove] if arg1 is a string, then arg2 must be passed")
                return
            else:
                self.__remove_kv(arg1, arg2, {})
        else:
            for k, v in arg1.items():
                self.__remove_kv(k, v, arg1)

    def unset(self, key):
        """
        Usage:
        1. unset(k)
        2. unset([k1, k2])

        :param key: one of [str, list[str]]
        :return:
        """
        if isinstance(key, (str, list, tuple)):
            self.__errors.append("[unset] key must be either String or List[string]")
            return
        if isinstance(key, (str,)):
            # ---- validate key
            key, is_k_valid = self.__validate_key_basic(key, "unset")
            if not is_k_valid:
                return
            # ----
            self.__list_unset.append(key)
        else:
            for k in key:
                # ---- validate key
                k, is_k_valid = self.__validate_key_basic(k, "unset")
                if not is_k_valid:
                    return
                # ----
                self.__list_unset.append(k)

    # ------------------------
    def __validate_key_basic(self, key, method_name):
        if not isinstance(key, (str,)):
            self.__errors.append(f"[{method_name}] skipping key: {key}. key must be a string")
            return key, False
        key = key.strip()
        if not key:
            self.__errors.append(f"[{method_name}] skipping key: {key}. empty string")
            return key, False
        # -----
        return key, True

    def __validate_key_prefix(self, key, method_name):
        if key not in ALL_RESERVED_KEYS:
            prefix_3_chars = key[:3].lower()
            if prefix_3_chars.startswith("$") or prefix_3_chars == "ss_":
                self.__errors.append(f"[{method_name}] skipping key: {key}. key starting with [$,ss_] are reserved")
                return False
        # ----
        return True

    def __is_identity_key(self, key):
        return key in IDENT_KEYS_ALL

    # -------------------------
    def __append_kv(self, key, val, kwargs):
        key, is_k_valid = self.__validate_key_basic(key, "append")
        if not is_k_valid:
            return
        if self.__is_identity_key(key):
            self.__add_identity(key, val, kwargs)
        else:
            is_k_valid = self.__validate_key_prefix(key, "append")
            if is_k_valid:
                self.__dict_append[key] = val

    def __remove_kv(self, key, val, kwargs):
        key, is_k_valid = self.__validate_key_basic(key, "remove")
        if not is_k_valid:
            return
        if self.__is_identity_key(key):
            self.__remove_identity(key, val, kwargs)
        else:
            is_k_valid = self.__validate_key_prefix(key, "remove")
            if is_k_valid:
                self.__dict_remove[key] = val

    def __add_identity(self, key, val, kwargs):
        if key == IDENT_KEY_EMAIL:
            self.add_email(val)
        elif key == IDENT_KEY_SMS:
            self.add_sms(val)
        elif key == IDENT_KEY_WHATSAPP:
            self.add_whatsapp(val)
        elif key == IDENT_KEY_ANDROIDPUSH:
            self.add_androidpush(val, kwargs.get("$pushvendor"))
        elif key == IDENT_KEY_IOSPUSH:
            self.add_iospush(val, kwargs.get("$pushvendor"))
        elif key == IDENT_KEY_WEBPUSH:
            self.add_webpush(val, kwargs.get("$pushvendor"))

    def __remove_identity(self, key, value, kwargs):
        if key == IDENT_KEY_EMAIL:
            self.remove_email(val)
        elif key == IDENT_KEY_SMS:
            self.remove_sms(val)
        elif key == IDENT_KEY_WHATSAPP:
            self.remove_whatsapp(val)
        elif key == IDENT_KEY_ANDROIDPUSH:
            self.remove_androidpush(val, kwargs.get("$pushvendor"))
        elif key == IDENT_KEY_IOSPUSH:
            self.remove_iospush(val, kwargs.get("$pushvendor"))
        elif key == IDENT_KEY_WEBPUSH:
            self.remove_webpush(val, kwargs.get("$pushvendor"))

    # ------------------------
    def __check_ident_val_string(self, value, method_name):
        msg = "value must a string with proper value"
        if not isinstance(value, (str,)):
            self.__errors.append(f"[{method_name}] {msg}")
            return value, False
        value = value.strip()
        if not value:
            self.__errors.append(f"[{method_name}] {msg}")
            return value, False
        # --
        return value, True

    # ------------------------ Email
    def __validate_email(self, email, method_name):
        email, is_valid = self.__check_ident_val_string(email, method_name)
        if not is_valid:
            return email, False
        # --- validate basic regex
        msg = "value in email format required. e.g. user@example.com"
        min_length, max_length = 6, 127
        # ---
        m = email_regex_compiled.match(email)
        if m is None:
            self.__errors.append(f"[{method_name}] invalid value {email}. {msg}")
            return email, False
        if len(email) < min_length or len(email) > max_length:
            self.__errors.append(f"[{method_name}] invalid value {email}. must be 6 <= len(email) <= 127")
            return email, False
        # ---
        return email, True

    def add_email(self, value: str):
        value, is_valid = self.__validate_email(value, "add_email")
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_EMAIL] = value

    def remove_email(self, value: str):
        value, is_valid = self.__validate_email(value, "remove_email")
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_EMAIL] = value

    # ------------------------ Mobile no
    def __validate_mobile_no(self, mobile_no, method_name):
        mobile_no, is_valid = self.__check_ident_val_string(mobile_no, method_name)
        if not is_valid:
            return mobile_no, False
        # --- validate basic regex
        msg = "number must start with + and must contain country code. e.g. +41446681800"
        min_length = 8
        # ---
        m = mobile_regex_compiled.match(mobile_no)
        if m is None:
            self.__errors.append(f"[{method_name}] invalid value {mobile_no}. {msg}")
            return mobile_no, False
        if len(mobile_no) < min_length:
            self.__errors.append(f"[{method_name}] invalid value {mobile_no}. len(mobile_no) must be >= 8")
            return mobile_no, False
        # ---
        return mobile_no, True

    # ------------------------ SMS
    def add_sms(self, value: str):
        value, is_valid = self.__validate_mobile_no(value, "add_sms")
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_SMS] = value

    def remove_sms(self, value: str):
        value, is_valid = self.__validate_mobile_no(value, "remove_sms")
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_SMS] = value

    # ------------------------ Whatsapp
    def add_whatsapp(self, value: str):
        value, is_valid = self.__validate_mobile_no(value, "add_whatsapp")
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_WHATSAPP] = value

    def remove_whatsapp(self, value: str):
        value, is_valid = self.__validate_mobile_no(value, "remove_whatsapp")
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_WHATSAPP] = value

    # ------------------------ Androidpush [providers: fcm / xiaomi / oppo]
    def __check_androidpush_value(self, value, provider, method_name):
        value, is_valid = self.__check_ident_val_string(value, method_name)
        if not is_valid:
            return value, provider, False
        # -- validate provider
        if not provider:
            provider = "fcm"
        if provider not in ["fcm", "xiaomi", "oppo"]:
            self.__errors.append(f"[{method_name}] unsupported androidpush provider {provider}")
            return value, provider, False
        # ---
        return value, provider, True

    def add_androidpush(self, value: str, provider: str = "fcm"):
        value, provider, is_valid = self.__check_androidpush_value(value, provider, "add_androidpush")
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_ANDROIDPUSH] = value
        self.__dict_append["$pushvendor"] = provider

    def remove_androidpush(self, value: str, provider: str = "fcm"):
        value, provider, is_valid = self.__check_androidpush_value(value, provider, "remove_androidpush")
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_ANDROIDPUSH] = value
        self.__dict_remove["$pushvendor"] = provider

    # ------------------------ Iospush [providers: apns]
    def __check_iospush_value(self, value, provider, method_name):
        value, is_valid = self.__check_ident_val_string(value, method_name)
        if not is_valid:
            return value, provider, False
        # -- validate provider
        if not provider:
            provider = "apns"
        if provider not in ["apns", ]:
            self.__errors.append(f"[{method_name}] unsupported iospush provider {provider}")
            return value, provider, False
        # ---
        return value, provider, True

    def add_iospush(self, value: str, provider: str = "apns"):
        value, provider, is_valid = self.__check_iospush_value(value, provider, "add_iospush")
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_IOSPUSH] = value
        self.__dict_append["$pushvendor"] = provider

    def remove_iospush(self, value: str, provider: str = "apns"):
        value, provider, is_valid = self.__check_iospush_value(value, provider, "remove_iospush")
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_IOSPUSH] = value
        self.__dict_remove["$pushvendor"] = provider

    # ------------------------ Webpush [providers: vapid]
    def __check_webpush_dict(self, value, provider, method_name):
        msg = "value must a valid webpush dict"
        if not (value and isinstance(value, (dict,))):
            self.__errors.append(f"[{method_name}] {msg}")
            return value, provider, False
        # -- validate provider
        if not provider:
            provider = "vapid"
        if provider not in ["vapid", ]:
            self.__errors.append(f"[{method_name}] unsupported webpush provider {provider}")
            return value, provider, False
        # ---
        return value, provider, True

    def add_webpush(self, value: dict, provider: str = "vapid"):
        value, provider, is_valid = self.__check_webpush_dict(value, provider, "add_webpush")
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_WEBPUSH] = value
        self.__dict_append["$pushvendor"] = provider

    def remove_webpush(self, value: dict, provider: str = "vapid"):
        value, provider, is_valid = self.__check_webpush_dict(value, provider, "remove_webpush")
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_WEBPUSH] = value
        self.__dict_remove["$pushvendor"] = provider

    # ------------------------
