import os
import base64
import magic
from typing import Dict


def check_is_web_url(file_path: str):
    for url_scheme in ["https://", "http://"]:
        if file_path.startswith(url_scheme):
            return True
    return False


def get_attachment_json_for_file(file_path: str, file_name: str, ignore_if_error: bool) -> Dict:
    # Ensure that path is expanded and absolute
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    # Get attachment json
    try:
        with open(abs_path, "rb") as f:
            final_file_name = os.path.basename(abs_path)
            if file_name and file_name.strip():
                final_file_name = file_name.strip()
            # --
            mime_type = magic.from_file(abs_path, mime=True)
            # base64 encoded string
            b64encoded = base64.b64encode(f.read())
            b64data = b64encoded.decode()
            attach_data = {
                "filename": final_file_name,
                "contentType": mime_type,
                "data": b64data,
                "url": None,
                "ignore_if_error": ignore_if_error,
            }
            return attach_data
    except OSError as ex:
        if ignore_if_error:
            print("WARNING: ignoring error while processing attachment file.", ex)
            return None
        else:
            raise ex


def get_attachment_json_for_url(file_url: str, file_name: str, ignore_if_error: bool) -> Dict:
    return {
        "filename": file_name,
        "contentType": None,
        "data": None,
        "url": file_url,
        "ignore_if_error": ignore_if_error,
    }


def get_attachment_json(file_path: str, file_name: str = None, ignore_if_error: bool = False) -> Dict:
    if check_is_web_url(file_path):
        return get_attachment_json_for_url(file_path, file_name, ignore_if_error)
    else:
        return get_attachment_json_for_file(file_path, file_name, ignore_if_error)
