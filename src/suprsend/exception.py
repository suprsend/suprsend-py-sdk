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


class SuprsendConfigError(SuprsendError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SuprsendAuthenticationError(SuprsendError):
    """
    Invalid auth
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 401
        self.error_type = "SuprsendAuthenticationError"
        if self.message is None:
            self.message = "Authentication failed"


class SuprsendAuthorizationError(SuprsendError):
    """
    client does not have authorization to access API.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 403
        self.error_type = "SuprsendAuthorizationError"
        if self.message is None:
            self.message = "Authorization failed"


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
