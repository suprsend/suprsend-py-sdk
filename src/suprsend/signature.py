import hashlib
import hmac
import base64
import json
from typing import Dict, Tuple
from urllib.parse import urlparse


def get_request_signature(url: str, http_verb: str, content: Dict, headers: Dict, secret: str) -> Tuple[str, str]:
    if http_verb == "GET":  # POST/GET/PUT
        content_txt, content_md5 = "", ""
    else:
        content_txt = json.dumps(content, ensure_ascii=False)
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
    # print("string_to_sign", string_to_sign)
    # ----- HMAC-SHA-256
    sig_hexdigest = hmac.HMAC(secret.encode(), msg=string_to_sign.encode(), digestmod=hashlib.sha256).digest()
    # -----
    sig = base64.b64encode(sig_hexdigest).decode()  # decode('utf-8'/'ascii')
    return content_txt, sig


def get_uri(url: str) -> str:
    o_url = urlparse(url)
    request_uri = o_url.path
    if o_url.query:
        request_uri = "{}?{}".format(request_uri, o_url.query)

    return request_uri
