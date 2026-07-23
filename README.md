# suprsend-py-sdk
This package can be included in a python3 project to easily integrate
with `SuprSend` platform.

### Installation
`suprsend-py-sdk` is available on PyPI. You can install using pip.
```bash
pip install suprsend-py-sdk
```

#### Optional: Better attachment MIME type detection
When adding file attachments, the SDK needs to detect the file's MIME type (e.g. `application/pdf`, `image/png`).
By default, it uses Python's built-in `mimetypes` module, which guesses based on the file extension.

For more accurate detection based on actual file content, install with the `magic` extra:
```bash
pip install suprsend-py-sdk[magic]
```
This requires the `libmagic` system library:
```bash
# On debian based systems
sudo apt install libmagic1

# If you are using macOS
brew install libmagic
```

### Usage
Initialize the SuprSend SDK
```python3
from suprsend import Suprsend
# Initialize SDK
supr_client = Suprsend("workspace_key", "workspace_secret")
```

Following example shows a sample request for triggering a workflow.
It triggers a pre-created workflow `purchase-made` to a recipient with id: `distinct_id`,
email: `user@example.com` & androidpush(fcm-token): `__android_push_fcm_token__`


```python3
from suprsend import WorkflowTriggerRequest
# Prepare Workflow body
wf = WorkflowTriggerRequest(
  body={
    "workflow": "purchase-made",
    "recipients": [
        {
          "distinct_id": "0f988f74-6982-41c5-8752-facb6911fb08",
          # if $channels is present, communication will be tried on mentioned channels only (for this request).
          # "$channels": ["email"],
          "$email": ["user@example.com"],
          "$androidpush": [{"token": "__android_push_token__", "provider": "fcm", "device_id": ""}],
        }
    ],
    # data can be any json / serializable python-dictionary
    "data": {
        "first_name": "User",
        "spend_amount": "$10",
        "nested_key_example": {
            "nested_key1": "some_value_1",
            "nested_key2": {
              "nested_key3": "some_value_3",
            },
        }
    }
  }
)
# Trigger workflow
response = supr_client.workflows.trigger(wf)
print(response)
```
When you call `supr_client.workflows.trigger`, the SDK internally makes an HTTP call to SuprSend
Platform to register this request, and you'll immediately receive a response indicating
the acceptance status.

You can also pass `idempotency-key` while triggering a workflow. Maximum length of idempotency_key can be 64 chars.
idempotency_key has multiple uses e.g.
1. Avoid duplicate request. If Suprsend receives and processes a request with an idempotency_key,
   it will skip processing requests with same idempotency_key for next 24 hours.
2. You can use this key to track webhooks related to workflow notifications.

```python3
from suprsend import WorkflowTriggerRequest

workflow_body = {...}
wf = WorkflowTriggerRequest(body=workflow_body, idempotency_key="__uniq_request_id__")
# You can also pass the tenant_id on behalf of which the workflow is to run.
wf = WorkflowTriggerRequest(body=workflow_body, idempotency_key="__uniq_request_id__", tenant_id="default")
# Trigger workflow
response = supr_client.workflows.trigger(wf)
print(response)
```

Note: The actual processing/execution of workflow happens asynchronously.

```python
# If the call succeeds, response will looks like:
{
    "success": True,
    "status": "success",
    "status_code": 202,
    "message": "Message received",
}

# In case the call fails. You will receive a response with success=False
{
    "success": False,
    "status": "fail",
    "status_code": 400/500,
    "message": "error message",
}
```

### Add attachments

To add one or more Attachments to a Workflow/Notification (viz. Email),
call `WorkflowTriggerRequest.add_attachment(file_path)`.
If providing a local path, ensure that it is proper, otherwise it will raise FileNotFoundError.
```python
from suprsend import WorkflowTriggerRequest
workflow_body = {...}
wf_instance = WorkflowTriggerRequest(body=workflow_body)

# this snippet can be used to add attachment to workflow.
file_path = "/home/user/billing.pdf"
wf_instance.add_attachment(file_path)
```

#### Attachment structure
The `add_attachment(...)` call appends below structure to `body->data->'$attachments'`

```json
{
    "filename": "billing.pdf",
    "contentType": "application/pdf",
    "data": "Q29uZ3JhdHVsYXRpb25zLCB5b3UgY2FuIGJhc2U2NCBkZWNvZGUh",
}
```
Where
* `filename` - name of file.
* `contentType` - MIME-type of file content.
* `data` - base64-encoded content of file.

### Limitation
* a single workflow body size must not exceed 800KB (800 * 1024 bytes).
* if size exceeds above mentioned limit, SDK raises python's builtin ValueError.

### Bulk API for Workflow Requests
You can send bulk request for workflows in one call. Use `.append()` on bulk_workflows instance
to add however-many-records to call in bulk.
```python3
from suprsend import WorkflowTriggerRequest

bulk_ins = supr_client.workflows.bulk_trigger_instance()

# one or more workflow instances
workflow1 = WorkflowTriggerRequest(body={...}) # body must be a proper workflow request json/dict
workflow2 = WorkflowTriggerRequest(body={...}) # body must be a proper workflow request json/dict

# --- use .append on bulk instance to add one or more records
bulk_ins.append(workflow1)
bulk_ins.append(workflow2)
# OR
bulk_ins.append(workflow1, workflow2)

# -------
response = bulk_ins.trigger()

print(response)
```
* There isn't any limit on number-of-records that can be added to bulk_workflows instance.
* On calling `bulk_ins.trigger()` the SDK internally makes one-or-more Callable-chunks.
* each callable-chunk contains a subset of records, the subset calculation is based on each record's bytes-size
  and max allowed chunk-size and chunk-length etc.
* for each callable-chunk SDK makes an HTTP call to SuprSend To register the request.

### Set channels in User Profile
If you regularly trigger a workflow for users on some pre-decided channels,
then instead of adding user-channel-details in each workflow request, you can set those channel-details in user
profile once, and after that, in workflow trigger request you only need to pass the distinct_id of the user.
All associated channels in User profile will be automatically picked when executing the workflow.

- First Instantiate a user object
```python
distinct_id = "__uniq_user_id__"  # Unique id of user in your application
# Instantiate User profile
user = supr_client.users.get_edit_instance(distinct_id=distinct_id)
```
- To add channel details to this user (viz. email, sms, whatsapp, androidpush, iospush etc)
  use `user.add_*` method(s) as shown in the example below.
```python
# Add channel details to user-instance. Call relevant add_* methods

user.add_email("user@example.com") # - To add Email

user.add_sms("+919999999999") # - To add SMS

user.add_whatsapp("+919999999999") # - To add Whatsapp

user.add_androidpush("__android_push_fcm_token__") # - by default, token is assumed to be fcm-token

# You can set the optional provider value [fcm/xiaomi/oppo] if its not a fcm-token
user.add_androidpush("__android_push_xiaomi_token__", provider="xiaomi")

user.add_iospush("__iospush_token__")

user.add_slack({"email": "user@example.com", "access_token": "xoxb-XXXXXXXXXXXX"})  # - DM user using email
user.add_slack({"user_id": "U03XXXXXXXX", "access_token": "xoxb-XXXXXXXXXXXX"})  # - DM user using slack member_id if known
user.add_slack({"channel_id": "C03XXXXXXXX", "access_token": "xoxb-XXXXXXXXXXXX"})  # - Use channel id
user.add_slack({"incoming_webhook": {"url": "https://hooks.slack.com/services/TXXXXXXXXX/BXXXXXX/XXXXXXX"}})  # - Use incoming webhook

user.add_ms_teams({"tenant_id": "XXXXXXX", "service_url": "https://smba.trafficmanager.net/XXXXXXXXXX", "conversation_id": "XXXXXXXXXXXX"})  # - DM on Team's channel using conversation id
user.add_ms_teams({"tenant_id": "XXXXXXX", "service_url": "https://smba.trafficmanager.net/XXXXXXXXXX", "user_id": "XXXXXXXXXXXX"})  # - DM user using team user id
user.add_ms_teams({"incoming_webhook": {"url": "https://XXXXX.webhook.office.com/webhookb2/XXXXXXXXXX@XXXXXXXXXX/IncomingWebhook/XXXXXXXXXX/XXXXXXXXXX"}})  # - Use incoming webhook

# After setting the channel details on user-instance, call edit()/async_edit()
response = supr_client.users.edit(user)
print(response)
```
```python
# Response structure
{
    "success": True, # if true, request was accepted.
    "status": "success",
    "status_code": 202, # http status code
    "message": "OK",
}

{
    "success": False, # error will be present in message
    "status": "fail",
    "status_code": 500, # http status code
    "message": "error message",
}

```
- Similarly, If you want to remove certain channel details from user,
you can call `user.remove_*` method as shown in the example below.

```python

# Remove channel helper methods
user.remove_email("user@example.com")
user.remove_sms("+919999999999")
user.remove_whatsapp("+919999999999")
user.remove_androidpush("__android_push_fcm_token__")
user.remove_androidpush("__android_push_xiaomi_token__", provider="xiaomi")
user.remove_iospush("__iospush_token__")

user.remove_slack({"email": "user@example.com", "access_token": "xoxb-XXXXXXXXXXXX"})  # - DM user using email
user.remove_slack({"user_id": "U03XXXXXXXX", "access_token": "xoxb-XXXXXXXXXXXX"})  # - DM user using slack member_id if known
user.remove_slack({"channel_id": "C03XXXXXXXX", "access_token": "xoxb-XXXXXXXXXXXX"})  # - Use channel id
user.remove_slack({"incoming_webhook": {"url": "https://hooks.slack.com/services/TXXXXXXXXX/BXXXXXX/XXXXXXX"}})  # - Use incoming webhook

user.remove_ms_teams({"tenant_id": "XXXXXXX", "service_url": "https://smba.trafficmanager.net/XXXXXXXXXX", "conversation_id": "XXXXXXXXXXXX"})  # - DM on Team's channel using conversation id
user.remove_ms_teams({"tenant_id": "XXXXXXX", "service_url": "https://smba.trafficmanager.net/XXXXXXXXXX", "user_id": "XXXXXXXXXXXX"})  # - DM user using team user id
user.remove_ms_teams({"incoming_webhook": {"url": "https://XXXXX.webhook.office.com/webhookb2/XXXXXXXXXX@XXXXXXXXXX/IncomingWebhook/XXXXXXXXXX/XXXXXXXXXX"}})  # - Use incoming webhook

# save
response = supr_client.users.edit(user)
print(response)
```

- If you need to delete/unset all emails (or any other channel) of a user,
  you can call `unset` method on the user instance.
  The method accepts the channel key/s (a single key or list of keys)
```python
# --- To delete all emails associated with user
user.unset("$email")
response = supr_client.users.async_edit(user)
print(response)

# what value to pass to unset channels
# for email:                $email
# for whatsapp:             $whatsapp
# for SMS:                  $sms
# for androidpush tokens:   $androidpush
# for iospush tokens:       $iospush
# for webpush tokens:       $webpush
# for slack:                $slack
# for ms_teams:             $ms_teams

# --- multiple channels can also be deleted in one call by passing argument as a list
user.unset(["$email", "$sms", "$whatsapp"])
response = supr_client.users.async_edit(user)
```

- You can also set preferred language of user using `set_preferred_language(lang_code)`. Value for lang_code
  must be 2-letter code in the `ISO 639-1 Alpha-2 code` format.
  e.g. en (for English), es (for Spanish), fr (for French) etc.
```python
# --- Set 2-letter language code in "ISO 639-1 Alpha-2" format
user.set_preferred_language("en")
response = supr_client.users.async_edit(user)
print(response)
```

- You can also set timezone of user using `set_timezone(timezone)`. Value for timezone
  must be from amongst the IANA timezones as maintained in the latest release here:
  https://data.iana.org/time-zones/tzdb-2024a/zonenow.tab.
```python
# --- Set timezone property at user level in IANA timezone format
user.set_timezone("America/Los_Angeles")
response = supr_client.users.async_edit(user)
print(response)
```

- Note: After calling `add_*`/`remove_*`/`unset`/`set_*` methods, don't forget to call `edit()/async_edit()`. On call of edit()/async_edit(),
SDK sends the request to SuprSend platform to update the User-Profile.

Once channels details are set at User profile, you only have to mention the user's distinct_id
while triggering workflow. Associated channels will automatically be picked up from user-profile
while processing the workflow. In the example below, we are passing only distinct_id of the user:

```python3
from suprsend import WorkflowTriggerRequest

# Prepare Workflow body
request_body = {
    "workflow": "purchase-made",
    "recipients": [
        {
            "distinct_id": "0f988f74-6982-41c5-8752-facb6911fb08",
        }
    ],
    # data can be any json / serializable python-dictionary
    "data": {
        "first_name": "User",
        "spend_amount": "$10",
        "nested_key_example": {
            "nested_key1": "some_value_1",
            "nested_key2": {
              "nested_key3": "some_value_3",
            },
        }
    }
}
wf = WorkflowTriggerRequest(body=request_body)
# Trigger workflow
response = supr_client.workflows.trigger(wf)
print(response)
```
#### Bulk API for Users
You can send multiple user requests in one call. Use `.append()` on bulk_users instance
to add however-many-records to call in bulk.
```python3
bulk_ins = supr_client.users.get_bulk_edit_instance()
# Prepare multiple users
u1 = supr_client.users.get_edit_instance("distinct_id_1") # User 1
u1.add_email("u1@example.com")

u2 = supr_client.users.get_edit_instance("distinct_id_2") # User 2
u2.add_email("u2@example.com")

# --- use .append on bulk instance to add one or more records
bulk_ins.append(u1)
bulk_ins.append(u2)
# OR
bulk_ins.append(u1, u2)

# -------
response = bulk_ins.save()
print(response)

```

### Track and Send Event
You can track and send events to SuprSend platform by using `supr_client.track_event` method.
An event is composed of an `event_name`, tracked wrt a user: `distinct_id`, with event-attributes: `properties`

```python3
from suprsend import Event

# Example
distinct_id = "__uniq_user_id__" # Mandatory, Unique id of user in your application
event_name = "__event_name__"   # Mandatory, name of the event you're tracking
properties = {} # Optional, default=None, a dict representing event-attributes

event = Event(distinct_id=distinct_id, event_name=event_name, properties=properties)
# You can also add Idempotency-key
event = Event(distinct_id=distinct_id, event_name=event_name, properties=properties,
              idempotency_key="__uniq_request_id__")
# You can also pass the tenant_id to be used for templates/notifications
event = Event(distinct_id=distinct_id, event_name=event_name, properties=properties,
              idempotency_key="__uniq_request_id__", tenant_id="default")
# Send event
response = supr_client.track_event(event)
print(response)
```

```python
# Response structure
{
    "success": True, # if true, request was accepted.
    "status": "success",
    "status_code": 202, # http status code
    "message": "OK",
}

{
    "success": False, # error will be present in message
    "status": "fail",
    "status_code": 500, # http status code
    "message": "error message",
}

```

#### Bulk API for events
You can send multiple events in one call. Use `.append()` on bulk_events instance
to add however-many-records to call in bulk.
```python3
from suprsend import Event

bulk_ins = supr_client.bulk_events.new_instance()
# Example
e1 = Event("distinct_id1", "event_name1", {"k1": "v1"}) # Event 1
e2 = Event("distinct_id2", "event_name2", {"k2": "v2"}) # Event 2

# --- use .append on bulk instance to add one or more records
bulk_ins.append(e1)
bulk_ins.append(e2)
# OR
bulk_ins.append(e1, e2)

# -------
response = bulk_ins.trigger()
print(response)

```

### Messages API

#### List Messages
Fetch a paginated list of messages for your workspace. All filter parameters are optional.

```python3
# Basic call — returns first page with default limit
response = supr_client.messages.list()

# With filters
response = supr_client.messages.list({
    # Pagination
    "limit": 20,                            # records per page (default: 1000, max: 1000)
    "after": "__cursor__",                  # cursor for next page (from meta.after)
    "before": "__cursor__",                 # cursor for previous page (from meta.before)

    # Message filters
    "message_id": "__message_id__",         # filter by a specific message id
    "idempotency_key": "__idempotency_key__",

    # Recipient filters
    "recipient_id": ["user1", "user2"],     # recipient_id[] — filter by one or more recipient ids
    "tenant_id": "default",

    # Object recipient filters (both required together)
    "object_type": "__object_type__",
    "object_id": "__object_id__",

    # Workflow / execution filters
    "workflow_slug": "purchase-made",
    "execution_id": "__execution_id__",

    # Channel filter
    # valid: email, sms, whatsapp, androidpush, iospush, webpush, slack, ms_teams
    "channel": "email",

    # status[] — valid: triggered, delivered, delivery_failed, seen, clicked, dismissed, read, archived, unread
    "status": ["delivered", "seen"],

    # category[] filter
    "category": ["transactional"],

    # Campaign filter
    "is_campaign": False,

    # Date range filters (RFC3339 format)
    "created_at_gte": "2026-01-01T00:00:00Z",
    "created_at_lte": "2026-12-31T23:59:59Z",
})
print(response)
```

```python
# Response structure
{
    "meta": {
        "count": 150,       # total matching messages
        "limit": 20,        # limit used for this request
        "has_prev": True,   # whether a previous page exists
        "has_next": True,   # whether a next page exists
        "before": None,     # cursor for previous page, null if none
        "after": None,      # cursor for next page, null if none
    },
    "results": [
        {
            "message_id": "01KQVGPW9ZJKH6T5TSxxxxxxx",
            "created_at": "2025-08-27T15:24:38.14Z",
            "updated_at": "2025-08-27T15:24:41.00Z",
            "triggered_at": "2025-08-27T15:24:38.29Z",
            "delivered_at": "2025-08-27T15:24:41.037Z",
            "seen_at": "2025-08-27T15:24:45.65Z",
            "clicked_at": None,
            "dismissed_at": None,
            "read_at": None,
            "unread_at": None,
            "archived_at": None,
            "unarchived_at": None,
            "is_read": False,
            "is_archived": False,
            "status": "seen",
            "channel": "email",
            "category": "transactional",
            "idempotency_key": "8087c3e7-6612-4d16-9660-xxxxxxxx",
            "failure_reason": "",
            "recipient": {
                "$type": "user",
                "distinct_id": "user_123"
            },
            "parent_entity_id": "__object:TEAMS:teams_1",
            "parent_entity_type": "object",
            "vendor": {
                "name": "amazon_ses",
                "nickname": "AWS SES"
            },
            "execution_id": "dsl_w1_id3741_xxxxxxxx_0_1",
            "parent_execution_id": "dsl_w1_id3741_xxxxxxxx_0",
            "is_campaign": False,
            "tenant_id": "default",
            "workflow": {
                "slug": "purchase-made",
                "version_id": "wf_v_01KQVGxxxxxxx_chkp",
                "name": "Purchase Workflow",
                "node_ref": ""
            },
            "template": {
                "name": "Purchase Template",
                "slug": "amazon_ses",
                "version_no": 1
            },
            "channel_identity": {
                "email": "user@example.com"
            },
        }
    ]
}
```

#### Bulk Update Message Status
Update the status of one or more messages in a single call.
Valid actions: `seen`, `clicked`, `dismissed`, `read`, `unread`, `archived`, `unarchived`.

```python3
messages = [
    {"message_id": "__message_id_1__", "action": "read"},
    {"message_id": "__message_id_2__", "action": "archived"},
]
response = supr_client.messages.bulk_update(messages)
print(response)
```

```python
# Response structure — 202 Accepted
# Per-record result; check status_code per message_id
{
    "records": [
        {
            "message_id": "__message_id_1__",
            "status_code": 202,     # 202 success, 404 not found, 422 action not supported, 500 error
            "error": {              # present only on failure
                "type": "not_found",
                "message": "message not found"
            }
        },
        ...
    ]
}
```
