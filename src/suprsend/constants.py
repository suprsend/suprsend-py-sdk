# Default urls
DEFAULT_URL = "https://hub.suprsend.com/"
DEFAULT_UAT_URL = "https://collector-staging.suprsend.workers.dev/"

# a API call should not have apparent body size of more than 200KB
BODY_MAX_APPARENT_SIZE_IN_BYTES = 200 * 1024  # 200 * 1024
BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE = "200KB"

# in general url-size wont exceed 2048 chars or 2048 utf-8 bytes
ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES = 2100

# few keys added in-flight, amounting to almost 200 bytes increase per workflow-body
RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES = 200

# max workflow-records in one batch api call.
MAX_RECORDS_IN_BATCH = 10

ALLOW_ATTACHMENTS_IN_BATCH = False

# In TZ Format: "%a, %d %b %Y %H:%M:%S %Z"
HEADER_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"
