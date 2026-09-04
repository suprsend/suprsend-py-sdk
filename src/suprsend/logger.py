import logging
import sys

LIBRARY_LOGGER_NAME = "suprsend"
ss_logger = logging.getLogger(LIBRARY_LOGGER_NAME)

_REDACTED = "[REDACTED]"
_BEARER_PREFIX = "Bearer "
_SENSITIVE_HEADERS = frozenset({
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
})


def redact_header_value(name: str, value: str) -> str:
    key = (name or "").lower()
    if not isinstance(value, str):
        value = str(value)
    if key in ("authorization", "proxy-authorization"):
        if len(value) >= len(_BEARER_PREFIX) and value[:len(_BEARER_PREFIX)].lower() == _BEARER_PREFIX.lower():
            return value[:len(_BEARER_PREFIX)] + _REDACTED
        return _REDACTED
    if key in _SENSITIVE_HEADERS:
        return _REDACTED
    return value


def sanitized_headers(headers):
    if not headers:
        return {}
    return {k: redact_header_value(k, v) for k, v in headers.items()}


def _has_usable_handler(logger) -> bool:
    current = logger
    while current:
        for handler in current.handlers:
            if not isinstance(handler, logging.NullHandler):
                return True
        if not current.propagate:
            break
        current = current.parent
    return False


def set_logging(debug: bool):
    """When debug=True, set the library logger to DEBUG so HTTP dumps emit."""
    if not debug:
        return
    ss_logger.setLevel(logging.DEBUG)
    if _has_usable_handler(ss_logger):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    ss_logger.addHandler(handler)


def _emit_http_dump(dump: str):
    try:
        ss_logger.debug("%s", dump)
    except Exception:
        pass


def log_http_exchange(method: str, url: str, req_headers=None, req_body=None, resp=None, error=None):
    if not ss_logger.isEnabledFor(logging.DEBUG):
        return
    try:
        lines = [
            "HTTP ------------------",
            "METHOD:\t%s" % method,
            "URL:\t%s" % url,
            "HEADER:\t%s" % sanitized_headers(req_headers),
            "BODY:\t%s" % ("" if req_body is None else req_body),
        ]
        if error is not None:
            lines.append("ERROR:\t%s" % error)
        elif resp is not None:
            try:
                resp_body = resp.text
            except Exception:
                resp_body = "<unavailable>"
            lines.extend([
                "STATUS:\t%s" % getattr(resp, "status_code", ""),
                # "RESP_HEADER:\t%s" % sanitized_headers(getattr(resp, "headers", None)),
                "RESP_BODY:\t%s" % resp_body,
            ])
        lines.append("------------------")
        dump = "\n".join(lines)
    except Exception:
        return
    _emit_http_dump(dump)
