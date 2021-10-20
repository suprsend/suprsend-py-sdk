# suprsend-py-sdk
This package can be included in a python3 project to easily integrate
with `Suprsend` platform.

We're working towards creating SDK in other languages as well.

### Suprsend SDKs available in following languages
* python3 >= 3.7 (`suprsend-py-sdk`)

### Installation
`suprsend-py-sdk` is available on PyPI. You can install using pip.
```bash
$ pip cache purge && pip install suprsend-py-sdk
```


### Usage
Initialize the Suprsend SDK
```python3
from suprsend import Suprsend
# Initialize SDK
supr_client = Suprsend("env_key", "env_secret")
```

Following example shows a sample request for triggering a workflow.
It triggers a notification to a user with id: `distinct_id`,
email: `user@example.com` & androidpush-token: `__android_push_token__`
using template `purchase-made` and notification_category `system`

```python3
# Prepare Workflow body
workflow_body = {
    "name": "Purchase Workflow",
    "template": "purchase-made",
    "notification_category": "system",
    "delay": "15m",
    "users": [
        {
            "distinct_id": "0f988f74-6982-41c5-8752-facb6911fb08",
            "$email": ["user@example.com"],
            "$androidpush": ["__android_push_token__"],
        }
    ],
    "data": {
        "template": {
            "first_name": "User",
            "spend_amount": "$10"
        },
        "$attachments": [
            {
                "filename": "billing.pdf",
                "contentType": "application/pdf",
                "data": "Q29uZ3JhdHVsYXRpb25zLCB5b3UgY2FuIGJhc2U2NCBkZWNvZGUh",
            }
        ],
    }
}

# Trigger workflow
supr_client.trigger_workflow(workflow_body)

```
### Add attachments
Structure of an attachment
```json
// attachment-structure
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

To add one or more Attachments to a Notification (viz. Email, Whatsapp),
add an attachment-structure for each of the attachment-files
to `data->"$attachments"` as shown below.

```python
# this snippet can be used to create attachment-structure given a file_path.
file_path = "/home/user/billing.pdf"

resp = supr_client.get_attachment_json_for_file(file_path)
# if some error occurs while reading content, the call returns success=False
if resp["success"]:
   attachment = resp["attachment"]
   # add the attachment to workflow_body->data->$attachments
   if workflow_body["data"].get("$attachments") is None:
      workflow_body["data"]["$attachments"] = []
   workflow_body["data"]["$attachments"].append(attachment)
else:
    # Handle as per requirement.
    pass
```
