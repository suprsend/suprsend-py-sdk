import uuid
import time
import re


# ---------- Identity keys
IDENT_KEY_EMAIL="$email"
IDENT_KEY_SMS="$sms"
IDENT_KEY_ANDROIDPUSH="$androidpush"
IDENT_KEY_IOSPUSH="$iospush"
IDENT_KEY_WHATSAPP="$whatsapp"
IDENT_KEY_WEBPUSH="$webpush"

IDENT_KEYS_ALL = [IDENT_KEY_EMAIL, IDENT_KEY_SMS, IDENT_KEY_ANDROIDPUSH, IDENT_KEY_IOSPUSH,
                  IDENT_KEY_WHATSAPP, IDENT_KEY_WEBPUSH,]

KEY_PUSHVENDOR = "$pushvendor"

OTHER_RESERVED_KEYS = [
    "$messenger", "$inbox",
    KEY_PUSHVENDOR, "$device_id",
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


class _IdentityEventInternalHelper:
    """
    Internal helper class
    """
    def __init__(self, distinct_id, workspace_key):
        self.distinct_id = distinct_id
        self.workspace_key = workspace_key
        #
        self.__dict_append = {}
        self.__append_count = 0
        #
        self.__dict_remove = {}
        self.__remove_count = 0
        #
        self.__list_unset = []
        self.__unset_count = 0
        #
        self.__errors = []
        self.__info = []

    def reset(self):
        self.__dict_append, self.__dict_remove, self.__list_unset = {}, {}, []
        self.__append_count, self.__remove_count, self.__unset_count = 0, 0, 0
        self.__errors = []
        self.__info = []

    def get_identity_event(self):
        evt = self.__form_event()
        ret_val = {
            "errors": self.__errors,
            "info": self.__info,
            "event": evt,
            "append": self.__append_count,
            "remove": self.__remove_count,
            "unset": self.__unset_count,
        }
        self.reset()
        return ret_val

    def __form_event(self):
        if (self.__dict_append or self.__dict_remove or self.__list_unset):
            event = {
                "$insert_id": str(uuid.uuid4()).lower(),
                "$time": int(time.time() * 1000),
                "env": self.workspace_key,
                "distinct_id": self.distinct_id,
            }
            if self.__dict_append:
                event["$append"] = self.__dict_append
                self.__append_count += 1
            if self.__dict_remove:
                event["$remove"] = self.__dict_remove
                self.__remove_count += 1
            if self.__list_unset:
                event["$unset"] = self.__list_unset
                self.__unset_count += 1
            return event
        else:
            return None

    # ------------------------
    def __validate_key_basic(self, key, caller):
        if not isinstance(key, (str,)):
            self.__info.append(f"[{caller}] skipping key: {key}. key must be a string")
            return key, False
        key = key.strip()
        if not key:
            self.__info.append(f"[{caller}] skipping key: empty string")
            return key, False
        # -----
        return key, True

    def __validate_key_prefix(self, key, caller):
        if key not in ALL_RESERVED_KEYS:
            prefix_3_chars = key[:3].lower()
            if prefix_3_chars.startswith("$") or prefix_3_chars == "ss_":
                self.__info.append(f"[{caller}] skipping key: {key}. key starting with [$,ss_] are reserved")
                return False
        # ----
        return True

    def __is_identity_key(self, key):
        return key in IDENT_KEYS_ALL

    # -------------------------
    def _append_kv(self, key, val, kwargs, caller="append"):
        key, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        if self.__is_identity_key(key):
            self.__add_identity(key, val, kwargs, caller=caller)
        else:
            is_k_valid = self.__validate_key_prefix(key, caller)
            if is_k_valid:
                self.__dict_append[key] = val

    def _remove_kv(self, key, val, kwargs, caller="remove"):
        key, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        if self.__is_identity_key(key):
            self.__remove_identity(key, val, kwargs, caller=caller)
        else:
            is_k_valid = self.__validate_key_prefix(key, caller)
            if is_k_valid:
                self.__dict_remove[key] = val

    def _unset_k(self, key, caller="unset"):
        k, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        # ----
        self.__list_unset.append(k)

    def __add_identity(self, key, val, kwargs, caller):
        if key == IDENT_KEY_EMAIL:
            self._add_email(val, caller=caller)

        elif key == IDENT_KEY_SMS:
            self._add_sms(val, caller=caller)

        elif key == IDENT_KEY_WHATSAPP:
            self._add_whatsapp(val, caller=caller)

        elif key == IDENT_KEY_ANDROIDPUSH:
            self._add_androidpush(val, kwargs.get(KEY_PUSHVENDOR), caller=caller)
            if self.__dict_append.get(KEY_PUSHVENDOR):
                kwargs[KEY_PUSHVENDOR] = self.__dict_append.get(KEY_PUSHVENDOR)

        elif key == IDENT_KEY_IOSPUSH:
            self._add_iospush(val, kwargs.get(KEY_PUSHVENDOR), caller=caller)
            if self.__dict_append.get(KEY_PUSHVENDOR):
                kwargs[KEY_PUSHVENDOR] = self.__dict_append.get(KEY_PUSHVENDOR)

        elif key == IDENT_KEY_WEBPUSH:
            self._add_webpush(val, kwargs.get(KEY_PUSHVENDOR), caller=caller)
            if self.__dict_append.get(KEY_PUSHVENDOR):
                kwargs[KEY_PUSHVENDOR] = self.__dict_append.get(KEY_PUSHVENDOR)

    def __remove_identity(self, key, value, kwargs):
        if key == IDENT_KEY_EMAIL:
            self._remove_email(val, caller=caller)

        elif key == IDENT_KEY_SMS:
            self._remove_sms(val, caller=caller)

        elif key == IDENT_KEY_WHATSAPP:
            self._remove_whatsapp(val, caller=caller)

        elif key == IDENT_KEY_ANDROIDPUSH:
            self._remove_androidpush(val, kwargs.get(KEY_PUSHVENDOR), caller=caller)
            if self.__dict_remove.get(KEY_PUSHVENDOR):
                kwargs[KEY_PUSHVENDOR] = self.__dict_remove.get(KEY_PUSHVENDOR)

        elif key == IDENT_KEY_IOSPUSH:
            self._remove_iospush(val, kwargs.get(KEY_PUSHVENDOR), caller=caller)
            if self.__dict_remove.get(KEY_PUSHVENDOR):
                kwargs[KEY_PUSHVENDOR] = self.__dict_remove.get(KEY_PUSHVENDOR)

        elif key == IDENT_KEY_WEBPUSH:
            self._remove_webpush(val, kwargs.get(KEY_PUSHVENDOR), caller=caller)
            if self.__dict_remove.get(KEY_PUSHVENDOR):
                kwargs[KEY_PUSHVENDOR] = self.__dict_remove.get(KEY_PUSHVENDOR)

    # ------------------------
    def __check_ident_val_string(self, value, caller):
        msg = "value must a string with proper value"
        if not isinstance(value, (str,)):
            self.__errors.append(f"[{caller}] {msg}")
            return value, False
        value = value.strip()
        if not value:
            self.__errors.append(f"[{caller}] {msg}")
            return value, False
        # --
        return value, True

    # ------------------------ Email

    def __validate_email(self, email, caller):
        email, is_valid = self.__check_ident_val_string(email, caller)
        if not is_valid:
            return email, False
        # --- validate basic regex
        msg = "value in email format required. e.g. user@example.com"
        min_length, max_length = 6, 127
        # ---
        m = email_regex_compiled.match(email)
        if m is None:
            self.__errors.append(f"[{caller}] invalid value {email}. {msg}")
            return email, False
        if len(email) < min_length or len(email) > max_length:
            self.__errors.append(f"[{caller}] invalid value {email}. must be 6 <= len(email) <= 127")
            return email, False
        # ---
        return email, True

    def _add_email(self, value: str, caller: str):
        value, is_valid = self.__validate_email(value, caller)
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_EMAIL] = value

    def _remove_email(self, value: str, caller):
        value, is_valid = self.__validate_email(value, caller)
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_EMAIL] = value

    # ------------------------ Mobile no

    def __validate_mobile_no(self, mobile_no, caller):
        mobile_no, is_valid = self.__check_ident_val_string(mobile_no, caller)
        if not is_valid:
            return mobile_no, False
        # --- validate basic regex
        msg = "number must start with + and must contain country code. e.g. +41446681800"
        min_length = 8
        # ---
        m = mobile_regex_compiled.match(mobile_no)
        if m is None:
            self.__errors.append(f"[{caller}] invalid value {mobile_no}. {msg}")
            return mobile_no, False
        if len(mobile_no) < min_length:
            self.__errors.append(f"[{caller}] invalid value {mobile_no}. len(mobile_no) must be >= 8")
            return mobile_no, False
        # ---
        return mobile_no, True

    # ------------------------ SMS

    def _add_sms(self, value: str, caller: str):
        value, is_valid = self.__validate_mobile_no(value, caller)
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_SMS] = value

    def _remove_sms(self, value: str, caller: str):
        value, is_valid = self.__validate_mobile_no(value, caller)
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_SMS] = value

    # ------------------------ Whatsapp

    def _add_whatsapp(self, value: str, caller: str):
        value, is_valid = self.__validate_mobile_no(value, caller)
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_WHATSAPP] = value

    def _remove_whatsapp(self, value: str, caller: str):
        value, is_valid = self.__validate_mobile_no(value, caller)
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_WHATSAPP] = value

    # ------------------------ Androidpush [providers: fcm / xiaomi / oppo]

    def __check_androidpush_value(self, value, provider, caller):
        value, is_valid = self.__check_ident_val_string(value, caller)
        if not is_valid:
            return value, provider, False
        # -- validate provider
        if not provider:
            provider = "fcm"
        if provider not in ["fcm", "xiaomi", "oppo"]:
            self.__errors.append(f"[{caller}] unsupported androidpush provider {provider}")
            return value, provider, False
        # ---
        return value, provider, True

    def _add_androidpush(self, value: str, provider: str, caller: str):
        value, provider, is_valid = self.__check_androidpush_value(value, provider, caller)
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_ANDROIDPUSH] = value
        self.__dict_append[KEY_PUSHVENDOR] = provider

    def _remove_androidpush(self, value: str, provider: str, caller: str):
        value, provider, is_valid = self.__check_androidpush_value(value, provider, caller)
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_ANDROIDPUSH] = value
        self.__dict_remove[KEY_PUSHVENDOR] = provider

    # ------------------------ Iospush [providers: apns]

    def __check_iospush_value(self, value, provider, caller):
        value, is_valid = self.__check_ident_val_string(value, caller)
        if not is_valid:
            return value, provider, False
        # -- validate provider
        if not provider:
            provider = "apns"
        if provider not in ["apns", ]:
            self.__errors.append(f"[{caller}] unsupported iospush provider {provider}")
            return value, provider, False
        # ---
        return value, provider, True

    def _add_iospush(self, value: str, provider: str, caller: str):
        value, provider, is_valid = self.__check_iospush_value(value, provider, caller)
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_IOSPUSH] = value
        self.__dict_append[KEY_PUSHVENDOR] = provider

    def _remove_iospush(self, value: str, provider: str, caller: str):
        value, provider, is_valid = self.__check_iospush_value(value, provider, caller)
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_IOSPUSH] = value
        self.__dict_remove[KEY_PUSHVENDOR] = provider

    # ------------------------ Webpush [providers: vapid]

    def __check_webpush_dict(self, value, provider, caller):
        msg = "value must be a valid dict representing webpush-token"
        if not (value and isinstance(value, (dict,))):
            self.__errors.append(f"[{caller}] {msg}")
            return value, provider, False
        # -- validate provider
        if not provider:
            provider = "vapid"
        if provider not in ["vapid", ]:
            self.__errors.append(f"[{caller}] unsupported webpush provider {provider}")
            return value, provider, False
        # ---
        return value, provider, True

    def _add_webpush(self, value: dict, provider: str, caller: str):
        value, provider, is_valid = self.__check_webpush_dict(value, provider, caller)
        if not is_valid:
            return
        self.__dict_append[IDENT_KEY_WEBPUSH] = value
        self.__dict_append[KEY_PUSHVENDOR] = provider

    def _remove_webpush(self, value: dict, provider: str, caller: str):
        value, provider, is_valid = self.__check_webpush_dict(value, provider, caller)
        if not is_valid:
            return
        self.__dict_remove[IDENT_KEY_WEBPUSH] = value
        self.__dict_remove[KEY_PUSHVENDOR] = provider

    # ------------------------
