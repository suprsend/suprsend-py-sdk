import hashlib
import hmac
import base64
import json
from urllib.parse import urlparse


def create_request_signature(url, http_verb, content, headers, secret):
    if http_verb == "GET":  # POST/GET/PUT
        content_md5 = ""
    else:
        content_txt = json.dumps(content)
        content_md5 = hashlib.md5(content_txt.encode()).hexdigest()
    # ----
    request_uri = get_uri(url)
    # ----- Create string to sign
    string_to_sign = "{}\n{}\n{}\n{}\n{}".format(
        http_verb,
        content_md5,
        headers["Content-Type"],
        headers["Date"],
        request_uri
    )
    # ----- HMAC-SHA-256
    sig_hexdigest = hmac.HMAC(secret.encode(), msg=string_to_sign.encode(), digestmod=hashlib.sha256).hexdigest()
    # -----
    sig_b64bytes = base64.b64encode(sig_hexdigest.encode())
    sig = sig_b64bytes.decode()  # decode('utf-8'/'ascii')
    return sig


def get_uri(url):
    o_url = urlparse(url)
    request_uri = o_url.path
    if o_url.query:
        request_uri = "{}?{}".format(request_uri, o_url.query)

    return request_uri
