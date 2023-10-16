# suprsend-py-sdk
This package can be included in a python3 project to easily integrate
with `SuprSend` platform.

We're working towards creating SDK in other languages as well.

### SuprSend SDKs available in following languages
* python3 >= 3.7 (`suprsend-py-sdk`)
* node (`suprsend-node-sdk`)
* java (`suprsend-java-sdk`)

### Installation
`suprsend-py-sdk` is available on PyPI. You can install using pip.
```bash
pip install suprsend-py-sdk
```
This SDK depends on a system package called `libmagic`. You can install it as follows:
```bash
# On debian based systems
sudo apt install libmagic

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
It triggers a notification to a user with id: `distinct_id`,
email: `user@example.com` & androidpush(fcm-token): `__android_push_fcm_token__`
using template `purchase-made` and notification_category `system`

```python3
from suprsend import Workflow
# Prepare Workflow body
workflow_body = {
    "name": "Purchase Workflow",
    "template": "purchase-made",
    "notification_category": "system",
    # "delay": "15m",  # Check duration format below
    "users": [
        {
          "distinct_id": "0f988f74-6982-41c5-8752-facb6911fb08",
          # if $channels is present, communication will be tried on mentioned channels only.
          # "$channels": ["email"],
          "$email": ["user@example.com"],
          "$androidpush": [{"token": "__android_push_token__", "provider": "fcm", "device_id": ""}],
        }
    ],
    # delivery instruction. how should notifications be sent, and whats the success metric
    "delivery": {
        "smart": False,
        "success": "seen"
    },
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
wf = Workflow(body=workflow_body)
# Trigger workflow
response = supr_client.trigger_workflow(wf)
print(response)
```
When you call `supr_client.trigger_workflow`, the SDK internally makes an HTTP call to SuprSend
Platform to register this request, and you'll immediately receive a response indicating
the acceptance status.

You can also pass `idempotency-key` while triggering a workflow. Maximum length of idempotency_key can be 64 chars.
idempotency_key has multiple uses e.g.
1. Avoid duplicate request. If Suprsend receives and processes a request with an idempotency_key,
   it will skip processing requests with same idempotency_key for next 24 hours.
2. You can use this key to track webhooks related to workflow notifications.

```python3
from suprsend import Workflow

workflow_body = {...}
wf = Workflow(body=workflow_body, idempotency_key="__uniq_request_id__")
# You can also the brand_id to be used for templates/notifications
wf = Workflow(body=workflow_body, idempotency_key="__uniq_request_id__", brand_id="default")
# Trigger workflow
response = supr_client.trigger_workflow(wf)
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
### Duration Format
format for specifying duration: `[xx]d[xx]h[xx]m[xx]s`
Where
* `d` stands for days. value boundary: 0 <= `d`
* `h` stands for hours. value boundary: 0 <= `h` <= 23
* `m` stands for minutes. value boundary: 0 <= `m` <= 59
* `s` stands for seconds. value boundary: 0 <= `s` <= 59

Examples:
* 2 days, 3 hours, 12 minutes, 23 seconds -> 2d3h12m23s or 02d03h12m23s
* 48 hours -> 2d
* 30 hours -> 1d6h
* 300 seconds -> 5m
* 320 seconds -> 5m20s
* 60 seconds -> 1m

### Delivery instruction
All delivery options:
```python
delivery = {
    "smart": True/False,
    "success": "seen/interaction/<some-user-defined-success-event>",
    "time_to_live": "<TTL duration>",
    "mandatory_channels": [] # list of mandatory channels e.g ["email"]
}
```
Where
* `smart` (boolean) - whether to optimize for number of notifications sent?
  - Possible values: `True` / `False`
  - Default value: `False`
  - If False, then notifications are sent on all channels at once.
  - If True, then notifications are sent one-by-one (on regular interval controlled by `time_to_live`)
    on each channel until given `success`-metric is achieved.

* `success` - what is your measurement of success for this notification?
  - Possible values: `delivered` / `seen` / `interaction` / `<some-user-defined-success-event>`
  - Default value: `seen`
  - If `delivered`: If notification on any of the channels is successfully delivered, consider it a success.
  - If `seen`: If notification on any of the channels is seen by user, consider it a success.
  - If `interaction`: If notification on any of the channels is clicked/interacted by the user, consider it a success.
  - If `<some-user-defined-success-event>`: If certain event is done by user within the event-window (1 day), consider it a success.
    - currently, event-window is not configurable. default set to `1d` (1 day).
      success-event must happen within this event-window since notification was sent.

* `time_to_live` - What's your buffer-window for sending notification.
  - applicable when `smart`=True, otherwise ignored
  - Default value: `1h` (1 hour)
  - notification on each channel will be sent with time-interval of [`time_to_live / (number_of_valid_channels - 1))`] apart.
  - Currently, channels are tried in low-to-high notification-cost order based on `Notification Cost` mentioned in Vendor Config.
    If cost is not mentioned, it is considered `0` for order-calculation purpose.
  - Process will continue until all channels are exhausted or `success` metric is achieved, whichever occurs first.

* `mandatory_channels` - Channels on which notification has to be sent immediately (irrespective of notification-cost).
  - applicable when `smart`=True, otherwise ignored
  - Default value: [] (empty list)
  - possible channels: `email, sms, whatsapp, androidpush, iospush` etc.


If delivery instruction is not provided, then default value is
```python3
{
    "smart": False,
    "success": "seen"
}
```

### Add attachments

To add one or more Attachments to a Workflow/Notification (viz. Email),
call `Workflow.add_attachment(file_path)` for each file with local-path.
Ensure that file_path is proper, otherwise it will raise FileNotFoundError.
```python
from suprsend import Workflow
workflow_body = {...}
wf_instance = Workflow(body=workflow_body)

# this snippet can be used to add attachment to workflow.
file_path = "/home/user/billing.pdf"
wf_instance.add_attachment(file_path)
```

#### Attachment structure
The `add_attachment(...)` call appends below structure to `workflow_body->data->'$attachments'`

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
from suprsend import Workflow

bulk_ins = supr_client.bulk_workflows.new_instance()

# one or more workflow instances
workflow1 = Workflow(body={...}) # body must be a proper workflow request json/dict
workflow2 = Workflow(body={...}) # body must be a proper workflow request json/dict

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
user = supr_client.user.get_instance(distinct_id=distinct_id)
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

# After setting the channel details on user-instance, call save()
response = user.save()
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
response = user.save()
print(response)
```

- If you need to delete/unset all emails (or any other channel) of a user,
  you can call `unset` method on the user instance.
  The method accepts the channel key/s (a single key or list of keys)
```python
# --- To delete all emails associated with user
user.unset("$email")
response = user.save()
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
user.save()
```

- You can also set preferred language of user using `set_preferred_language(lang_code)`. Value for lang_code
  must be 2-letter code in the `ISO 639-1 Alpha-2 code` format.
  e.g. en (for English), es (for Spanish), fr (for French) etc.
```python
# --- Set 2-letter language code in "ISO 639-1 Alpha-2" format
user.set_preferred_language("en")
response = user.save()
print(response)
```

- Note: After calling `add_*`/`remove_*`/`unset`/`set_*` methods, don't forget to call `user.save()`. On call of save(),
SDK sends the request to SuprSend platform to update the User-Profile.

Once channels details are set at User profile, you only have to mention the user's distinct_id
while triggering workflow. Associated channels will automatically be picked up from user-profile
while processing the workflow. In the example below, we are passing only distinct_id of the user:

```python3
from suprsend import Workflow

# Prepare Workflow body
workflow_body = {
    "name": "Purchase Workflow",
    "template": "purchase-made",
    "notification_category": "system",
    # "delay": "15m",
    "users": [
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
wf = Workflow(body=workflow_body)
# Trigger workflow
response = supr_client.trigger_workflow(wf)
print(response)
```
#### Bulk API for Users
You can send multiple subscriber requests in one call. Use `.append()` on bulk_users instance
to add however-many-records to call in bulk.
```python3
bulk_ins = supr_client.bulk_users.new_instance()
# Prepare multiple users
u1 = supr_client.user.get_instance("distinct_id_1") # User 1
u1.set_email("u1@example.com")

u2 = supr_client.user.get_instance("distinct_id_2") # User 2
u2.set_email("u2@example.com")

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
# You can also the brand_id to be used for templates/notifications
event = Event(distinct_id=distinct_id, event_name=event_name, properties=properties,
              idempotency_key="__uniq_request_id__", brand_id="default")
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
