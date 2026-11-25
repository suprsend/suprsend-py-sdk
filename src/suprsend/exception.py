from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from requests import Response


class SuprsendError(Exception):
    """
    A base class for all Suprsend exceptions.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args)
        self.message = kwargs.get("message")
        if self.message is None and self.args and self.args[0]:
            self.message = self.args[0]
        elif self.message is None:
            self.message = None
        self.status_code = kwargs.get("status_code", 500)

    def __str__(self) -> str:
        return f"[code: {self.status_code}] {self.message}"


class SuprsendAPIException(SuprsendError):
    response: Optional["Response"] = None
    message = "unknown error"

    def __init__(self, response: "Response") -> None:
        # -- Get error message
        content_type = response.headers.get("Content-Type")
        if content_type and "application/json" in content_type:
            try:
                rjson = response.json()
                err_msg = rjson.get("message") or rjson.get("detail")
            except:
                err_msg = response.text
        else:
            err_msg = response.text
        message = f"{err_msg}"
        # --
        super().__init__(message=message, status_code=response.status_code)
        self.response = response


class InputValueError(ValueError):
    pass


class SuprsendConfigError(SuprsendError):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class SuprsendMissingSchema(SuprsendError):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.status_code = 500
        self.error_type = "SuprsendMissingSchema"
        if self.message is None:
            self.message = "Missing JSON schema"


class SuprsendInvalidSchema(SuprsendError):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.status_code = 500
        self.error_type = "SuprsendInvalidSchema"
        if self.message is None:
            self.message = "Invalid JSON schema"


class SuprsendValidationError(SuprsendError):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.status_code = 400
        self.error_type = "SuprsendValidationError"
        if self.message is None:
            self.message = "validation error"
