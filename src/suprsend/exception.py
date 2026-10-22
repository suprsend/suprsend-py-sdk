class SuprsendError(Exception):
    """
    A base class for all Suprsend exceptions.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.message = kwargs.get('message')
        if self.message is None and self.args and self.args[0]:
            self.message = self.args[0]
        elif self.message is None:
            self.message = None
        self.status_code = kwargs.get('status_code', 500)

    def __str__(self):
        return f"[code: {self.status_code}] {self.message}"


class SuprsendAPIException(SuprsendError):
    response = None
    message = "unknown error"
    # max chars of a raw (non-JSON) response body kept in the message
    MAX_RAW_TEXT_LEN = 1000

    def __init__(self, response):
        # -- Get error message
        err_msg = None
        content_type = response.headers.get("Content-Type") or ""
        if "application/json" in content_type:
            try:
                rjson = response.json()
            except Exception:
                rjson = None
            if isinstance(rjson, dict):
                err = rjson.get("error")
                if isinstance(err, dict):
                    err = err.get("message")
                err_msg = rjson.get("message") or rjson.get("detail") or err
        # -- HTML bodies (e.g. gateway error pages) carry no useful message
        if not err_msg and "text/html" not in content_type:
            err_msg = (response.text or "").strip()
            if len(err_msg) > self.MAX_RAW_TEXT_LEN:
                err_msg = err_msg[:self.MAX_RAW_TEXT_LEN] + "..."
        if not err_msg:
            err_msg = getattr(response, "reason", None) or "unknown error"
        message = f"{err_msg}"
        # --
        super().__init__(message=message, status_code=response.status_code)
        self.response = response


class InputValueError(ValueError):
    pass


class SuprsendConfigError(SuprsendError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SuprsendMissingSchema(SuprsendError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 500
        self.error_type = "SuprsendMissingSchema"
        if self.message is None:
            self.message = "Missing JSON schema"


class SuprsendInvalidSchema(SuprsendError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 500
        self.error_type = "SuprsendInvalidSchema"
        if self.message is None:
            self.message = "Invalid JSON schema"


class SuprsendValidationError(SuprsendError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 400
        self.error_type = "SuprsendValidationError"
        if self.message is None:
            self.message = "validation error"
