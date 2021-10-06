import logging
from http.client import HTTPConnection
# Enabling debugging at http.client level (requests->urllib3->http.client)
# you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# the only thing missing will be the response.body which is not logged.
requests_log = None

logging.basicConfig()  # you need to initialize logging, otherwise you will not see anything from requests


def set_logging(level=0):
    global requests_log
    if level > 0:
        HTTPConnection.debuglevel = 1
        #
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
    else:
        HTTPConnection.debuglevel = 0
        #
        logging.getLogger().setLevel(logging.WARN)
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.WARN)
        requests_log.propagate = True
