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
pip cache purge && pip install suprsend-py-sdk
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

# Trigger workflow
response = supr_client.trigger_workflow(workflow_body)

```
When you call `supr_client.trigger_workflow`, the SDK internally makes an HTTP call to SuprSend
Platform to register this request, and you'll immediately receive a response indicating
the acceptance status.

Note: The actual processing/execution of workflow happens asynchronously.

```python
# If the call succeeds, response will looks like:
{
    "success": True,
    "status": 201,
    "message": "Message received",
}

# In case the call fails. You will receive a response with success=False
{
    "success": False,
    "status": 400,
    "message": "error message",
}
```

### Add attachments

To add one or more Attachments to a Notification (viz. Email, Whatsapp),
call `supr_client.add_attachment(...)` for each file.
Ensure that file_path is proper, otherwise it will raise FileNotFoundError.
```python
# this snippet can be used to add attachment to workflow_body.
file_path = "/home/user/billing.pdf"
supr_client.add_attachment(workflow_body, file_path)
```

#### Attachment structure
The `add_attachment(...)` call appends below structure to `data->'$attachments'`

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
* a single workflow body size must not exceed 200KB (200 * 1024 bytes). While calculating size, attachments are ignored
* if size exceeds above mentioned limit, SDK raises python's builtin ValueError.

### Request-Batching
You can batch multiple workflow requests in one call. Use `batch_instance.append(...)` on batch-instance
to add however-many-records to call in batch.
```python3
batch_ins = supr_client.batch.new()

workflow_body1 = {...}  # must be a proper workflow request json/dict
workflow_body2 = {...}  # must be a proper workflow request json/dict

# --- use .append on batch instance to add one or more records
batch_ins.append(workflow_body1)
batch_ins.append(workflow_body2)
# OR
batch_ins.append(workflow_body1, workflow_body2)

# -------
response = batch_ins.trigger()

print(response)
```
* There isn't any limit on number-of-records that can be added to batch-instance.
* On calling `batch_ins.trigger()` the SDK internally makes one-or-more Callable-chunks.
* each callable-chunk contains a subset of records, the subset calculation is based on each record's bytes-size
  and max allowed chunk-size and chunk-length.
* for each callable-chunk SDK makes an HTTP call to SuprSend To register the request.
