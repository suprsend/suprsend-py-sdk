# suprsend-py-sdk
This package can be included in a python3 project to easily integrate
with `Suprsend` platform.

We're working towards creating SDK in other languages as well.

### Suprsend SDKs available in below languages
* python3 (`suprsend-py-sdk`)

### Installation
$ pip install suprsend-py-sdk

### Usage
Initialize the Suprsend SDK
```python3
from suprsend import Suprsend
# Initialize SDK
supr_client = Suprsend("env_key", "env_secret")
```

Example Below shows a sample request for triggering a workflow.
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
        }
    }
}

# Trigger workflow
supr_client.trigger_workflow(workflow_body)

```

### Build and upload
Setup a python3 virtualenv `venv_sdk` for building this lib.
```bash
virtualenv -p python3 venv_sdk
source venv_sdk/bin/activate
python3 -m pip install --upgrade build
python3 -m pip install --upgrade twine
```
Build package
```bash
python3 -m build
# On test.pypi.org
python3 -m twine upload --repository testpypi dist/*
# On pypi.org
python3 -m twine upload dist/*
```
Installing newly uploaded package 
```bash
python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps suprsend-py-sdk
```
