# Default urls
DEFAULT_URL = "https://hub.suprsend.com/"
DEFAULT_UAT_URL = "https://collector-staging.suprsend.workers.dev/"

# an Event should not have apparent body size of more than 100KB
SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES = 100 * 1024  # 100 * 1024
SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE = "100KB"

# a API call should not have apparent body size of more than 800KB
BODY_MAX_APPARENT_SIZE_IN_BYTES = 800 * 1024  # 800 * 1024
BODY_MAX_APPARENT_SIZE_IN_BYTES_READABLE = "800KB"

# in general url-size wont exceed 2048 chars or 2048 utf-8 bytes
ATTACHMENT_URL_POTENTIAL_SIZE_IN_BYTES = 2100

# few keys added in-flight, amounting to almost 200 bytes increase per workflow-body
WORKFLOW_RUNTIME_KEYS_POTENTIAL_SIZE_IN_BYTES = 200

# max workflow-records in one bulk api call.
MAX_WORKFLOWS_IN_BULK_API = 100
# max event-records in one bulk api call
MAX_EVENTS_IN_BULK_API = 100

ALLOW_ATTACHMENTS_IN_BULK_API = True
ATTACHMENT_UPLOAD_ENABLED = False

# -- single Identity event limit
IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES = 10 * 1024
IDENTITY_SINGLE_EVENT_MAX_APPARENT_SIZE_IN_BYTES_READABLE = "10KB"

MAX_IDENTITY_EVENTS_IN_BULK_API = 400

# In TZ Format: "%a, %d %b %Y %H:%M:%S %Z"
HEADER_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"
