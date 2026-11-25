from typing import Any

# ---------- Identity keys
IDENT_KEY_EMAIL = "$email"
IDENT_KEY_SMS = "$sms"
IDENT_KEY_ANDROIDPUSH = "$androidpush"
IDENT_KEY_IOSPUSH = "$iospush"
IDENT_KEY_WHATSAPP = "$whatsapp"
IDENT_KEY_WEBPUSH = "$webpush"
IDENT_KEY_SLACK = "$slack"
IDENT_KEY_MS_TEAMS = "$ms_teams"

IDENT_KEYS_ALL = [
    IDENT_KEY_EMAIL,
    IDENT_KEY_SMS,
    IDENT_KEY_ANDROIDPUSH,
    IDENT_KEY_IOSPUSH,
    IDENT_KEY_WHATSAPP,
    IDENT_KEY_WEBPUSH,
    IDENT_KEY_SLACK,
    IDENT_KEY_MS_TEAMS,
]

KEY_ID_PROVIDER = "$id_provider"
KEY_BUNDLE_ID = "$bundle_id"
KEY_PREFERRED_LANGUAGE = "$preferred_language"
KEY_LOCALE = "$locale"
KEY_TIMEZONE = "$timezone"


class _UserEditInternalHelper:
    def __init__(self) -> None:
        self.__dict_set: dict[str, Any] = {}
        self.__dict_set_once: dict[str, Any] = {}
        self.__dict_increment: dict[str, Any] = {}
        self.__dict_append: dict[str, Any] = {}
        self.__dict_remove: dict[str, Any] = {}
        self.__list_unset: list[str] = []
        #
        self.__errors: list[str] = []
        self.__info: list[str] = []

    def reset(self) -> None:
        self.__dict_set, self.__dict_append, self.__dict_remove, self.__list_unset = {}, {}, {}, []
        self.__dict_set_once, self.__dict_increment = {}, {}
        self.__errors = []
        self.__info = []

    def get_operation_result(self) -> dict[str, Any]:
        operation = self.__form_operation()
        ret_val = {
            "errors": self.__errors,
            "info": self.__info,
            "operation": operation,
        }
        self.reset()
        return ret_val

    def __form_operation(self) -> dict[str, Any]:
        event: dict[str, Any] = {}
        if self.__dict_set:
            event["$set"] = self.__dict_set
        if self.__dict_set_once:
            event["$set_once"] = self.__dict_set_once
        if self.__dict_increment:
            event["$add"] = self.__dict_increment
        if self.__dict_append:
            event["$append"] = self.__dict_append
        if self.__dict_remove:
            event["$remove"] = self.__dict_remove
        if self.__list_unset:
            event["$unset"] = self.__list_unset
        return event

    # ------------------------
    def __validate_key_basic(self, key: str, caller: str) -> tuple[str, bool]:
        if not isinstance(key, (str,)):
            self.__info.append(f"[{caller}] skipping key: {key}. key must be a string")
            return key, False
        key = key.strip()
        if not key:
            self.__info.append(f"[{caller}] skipping key: empty string")
            return key, False
        # -----
        return key, True

    def __is_identity_key(self, key: str) -> bool:
        return key in IDENT_KEYS_ALL

    # -------------------------
    def _append_kv(self, key: str, val: Any, kwargs: dict[str, Any], caller: str = "append") -> None:
        key, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        if self.__is_identity_key(key):
            self.__add_identity(key, val, kwargs, caller=caller)
        else:
            self.__dict_append[key] = val

    def _remove_kv(self, key: str, val: Any, kwargs: dict[str, Any], caller: str = "remove") -> None:
        key, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        if self.__is_identity_key(key):
            self.__remove_identity(key, val, kwargs, caller=caller)
        else:
            self.__dict_remove[key] = val

    def _unset_k(self, key: str, caller: str = "unset") -> None:
        k, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        # ----
        self.__list_unset.append(k)

    def _set_kv(self, key: str, val: Any, caller: str = "set") -> None:
        key, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        else:
            self.__dict_set[key] = val

    def _set_once_kv(self, key: str, val: Any, caller: str = "set_once") -> None:
        key, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        else:
            self.__dict_set_once[key] = val

    def _increment_kv(self, key: str, val: int | float, caller: str = "increment") -> None:
        key, is_k_valid = self.__validate_key_basic(key, caller)
        if not is_k_valid:
            return
        else:
            self.__dict_increment[key] = val

    def _set_preferred_language(self, lang_code: str, caller: str) -> None:
        self.__dict_set[KEY_PREFERRED_LANGUAGE] = lang_code

    def _set_locale(self, locale_code: str, caller: str) -> None:
        self.__dict_set[KEY_LOCALE] = locale_code

    def _set_timezone(self, timezone: str, caller: str) -> None:
        self.__dict_set[KEY_TIMEZONE] = timezone

    def __add_identity(self, key: str, val: str | Any, kwargs: dict[str, Any], caller: str) -> None:
        new_caller = f"{caller}:{key}"
        if key == IDENT_KEY_EMAIL:
            self._add_email(val, caller=new_caller)

        elif key == IDENT_KEY_SMS:
            self._add_sms(val, caller=new_caller)

        elif key == IDENT_KEY_WHATSAPP:
            self._add_whatsapp(val, caller=new_caller)

        elif key == IDENT_KEY_ANDROIDPUSH:
            self._add_androidpush(val, kwargs.get(KEY_ID_PROVIDER), kwargs.get(KEY_BUNDLE_ID), caller=new_caller)

        elif key == IDENT_KEY_IOSPUSH:
            self._add_iospush(val, kwargs.get(KEY_ID_PROVIDER), kwargs.get(KEY_BUNDLE_ID), caller=new_caller)

        elif key == IDENT_KEY_WEBPUSH:
            self._add_webpush(val, kwargs.get(KEY_ID_PROVIDER), caller=new_caller)

        elif key == IDENT_KEY_SLACK:
            self._add_slack(val, caller=new_caller)

        elif key == IDENT_KEY_MS_TEAMS:
            self._add_ms_teams(val, caller=new_caller)

    def __remove_identity(self, key: str, val: str | Any, kwargs: dict[str, Any], caller: str) -> None:
        new_caller = f"{caller}:{key}"
        if key == IDENT_KEY_EMAIL:
            self._remove_email(val, caller=new_caller)

        elif key == IDENT_KEY_SMS:
            self._remove_sms(val, caller=new_caller)

        elif key == IDENT_KEY_WHATSAPP:
            self._remove_whatsapp(val, caller=new_caller)

        elif key == IDENT_KEY_ANDROIDPUSH:
            self._remove_androidpush(val, kwargs.get(KEY_ID_PROVIDER), kwargs.get(KEY_BUNDLE_ID), caller=new_caller)

        elif key == IDENT_KEY_IOSPUSH:
            self._remove_iospush(val, kwargs.get(KEY_ID_PROVIDER), kwargs.get(KEY_BUNDLE_ID), caller=new_caller)

        elif key == IDENT_KEY_WEBPUSH:
            self._remove_webpush(val, kwargs.get(KEY_ID_PROVIDER), caller=new_caller)

        elif key == IDENT_KEY_SLACK:
            self._remove_slack(val, caller=new_caller)

        elif key == IDENT_KEY_MS_TEAMS:
            self._remove_ms_teams(val, caller=new_caller)

    # ------------------------ Email
    def _add_email(self, value: str, caller: str) -> None:
        self.__dict_append[IDENT_KEY_EMAIL] = value

    def _remove_email(self, value: str, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_EMAIL] = value

    # ------------------------ SMS

    def _add_sms(self, value: str, caller: str) -> None:
        self.__dict_append[IDENT_KEY_SMS] = value

    def _remove_sms(self, value: str, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_SMS] = value

    # ------------------------ Whatsapp

    def _add_whatsapp(self, value: str, caller: str) -> None:
        self.__dict_append[IDENT_KEY_WHATSAPP] = value

    def _remove_whatsapp(self, value: str, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_WHATSAPP] = value

    # ------------------------ Androidpush

    def _add_androidpush(self, value: str, provider: str | None, bundle_id: str | None, caller: str) -> None:
        self.__dict_append[IDENT_KEY_ANDROIDPUSH] = value
        self.__dict_append[KEY_ID_PROVIDER] = provider
        if bundle_id:
            self.__dict_append[KEY_BUNDLE_ID] = bundle_id

    def _remove_androidpush(self, value: str, provider: str | None, bundle_id: str | None, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_ANDROIDPUSH] = value
        self.__dict_remove[KEY_ID_PROVIDER] = provider
        if bundle_id:
            self.__dict_remove[KEY_BUNDLE_ID] = bundle_id

    # ------------------------ Iospush

    def _add_iospush(self, value: str, provider: str | None, bundle_id: str | None, caller: str) -> None:
        self.__dict_append[IDENT_KEY_IOSPUSH] = value
        self.__dict_append[KEY_ID_PROVIDER] = provider
        if bundle_id:
            self.__dict_append[KEY_BUNDLE_ID] = bundle_id

    def _remove_iospush(self, value: str, provider: str | None, bundle_id: str | None, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_IOSPUSH] = value
        self.__dict_remove[KEY_ID_PROVIDER] = provider
        if bundle_id:
            self.__dict_remove[KEY_BUNDLE_ID] = bundle_id

    # ------------------------ Webpush

    def _add_webpush(self, value: Any, provider: str | None, caller: str) -> None:
        self.__dict_append[IDENT_KEY_WEBPUSH] = value
        self.__dict_append[KEY_ID_PROVIDER] = provider

    def _remove_webpush(self, value: Any, provider: str | None, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_WEBPUSH] = value
        self.__dict_remove[KEY_ID_PROVIDER] = provider

    # ------------------------ Slack

    def _add_slack(self, value: Any, caller: str) -> None:
        self.__dict_append[IDENT_KEY_SLACK] = value

    def _remove_slack(self, value: Any, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_SLACK] = value

    # ------------------------ MS Teams

    def _add_ms_teams(self, value: Any, caller: str) -> None:
        self.__dict_append[IDENT_KEY_MS_TEAMS] = value

    def _remove_ms_teams(self, value: Any, caller: str) -> None:
        self.__dict_remove[IDENT_KEY_MS_TEAMS] = value
