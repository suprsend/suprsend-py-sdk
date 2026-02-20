import logging
from http.client import HTTPConnection
# Enabling debugging at http.client level (requests->urllib3->http.client)
# you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# the only thing missing will be the response.body which is not logged.
requests_log = None
LIBRARY_LOGGER_NAME = "suprsend"
ss_logger = logging.getLogger(LIBRARY_LOGGER_NAME)


def set_logging(level=logging.WARN, http_debug = False):
    global requests_log

    # set library log level as per given.
    ss_logger.setLevel(level=level)

    # Set network log level to either debug or warning.
    HTTPConnection.debuglevel = 1 if http_debug else 0
    requests_log = logging.getLogger("urllib3")
    requests_log.setLevel(logging.DEBUG if http_debug else logging.WARN)
    requests_log.propagate = True