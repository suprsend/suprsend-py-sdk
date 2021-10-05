import json
from .exception import SuprsendMissingSchema, SuprsendConfigError


class Suprsend:
    DEFAULT_URL = "https://hub.suprsend.com/"

    def __init__(self, env_key, env_secret, post_url=None):
        self.env_key = env_key
        self.env_secret = env_secret
        if not post_url:
            post_url = self.DEFAULT_URL
        # -- check url ends with /
        post_url = post_url.strip()
        if post_url[len(post_url) - 1] != "/":
            post_url = post_url + "/"
        # ---
        self.base_url = post_url
        #
        self.__validate()

    def __validate(self):
        if not self.env_key:
            raise SuprsendConfigError("Missing env_key")
        if not self.env_secret:
            raise SuprsendConfigError("Missing env_secret")
        if not self.base_url:
            raise SuprsendConfigError("Missing base_url")


# Cached json schema
__JSON_SCHEMAS = dict()


def _get_schema(schema_name: str):
    schema_body = __JSON_SCHEMAS.get(schema_name)
    if not schema_body:
        schema_body = __load_json_schema(schema_name)
        if not schema_body:
            raise SuprsendMissingSchema(schema_name)
        else:
            __JSON_SCHEMAS[schema_name] = schema_body
    return schema_body


def __load_json_schema(schema_name: str) -> dict:
    file_path = "json/{}.json".format(schema_name)
    with open(file_path) as f:
        s = json.load(f)
        return s
