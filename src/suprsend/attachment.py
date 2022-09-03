import os
import base64
import magic
from typing import Dict


def get_attachment_json_for_file(file_path: str) -> Dict:
    # Ensure that path is expanded and absolute
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    # Get attachment json
    with open(abs_path, "rb") as f:
        file_name = os.path.basename(abs_path)
        mime_type = magic.from_file(abs_path, mime=True)
        # base64 encoded string
        b64encoded = base64.b64encode(f.read())
        b64data = b64encoded.decode()
        return {
            "filename": file_name,
            "contentType": mime_type,
            "data": b64data,
        }
