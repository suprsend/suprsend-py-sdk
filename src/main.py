from suprsend import Suprsend


def test_request():
    extra_params = {
        "is_uat": True, "auth_enabled": True,
        "include_signature_param": True
    }
    supr_client = Suprsend("__env_key__", "__env_secret__", debug=False, **extra_params)
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
    resp = supr_client.trigger_workflow(workflow_body)
    print(resp)


if __name__ == "__main__":
    test_request()
