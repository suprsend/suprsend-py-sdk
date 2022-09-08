from suprsend import Suprsend, Workflow


def test_request():
    supr_client = Suprsend("__workspace_key__", "__workspace_secret__", debug=True)
    workflow_body = {
        "name": "Purchase Workflow",
        "template": "purchase-made",
        "notification_category": "system",
        # "delay": "15m",
        "users": [
            {
                "distinct_id": "0f988f74-6982-41c5-8752-facb6911fb08",
                "$channels": ["email", "androidpush"],
                "$email": ["user@example.com"],
                "$androidpush": [{"token": "__android_push_token__", "provider": "fcm", "device_id": None}],
            }
        ],
        "delivery": {
            "smart": False,
            "mandatory_channels": ["email"]
        },
        "data": {
            "event": {
                "location": {
                    "city": 'mumbai'
                },
                "city": 'mumbai',
                "amount": "$10",
                "product_name": "Product A"
            },
            "template": {
                "first_name": "User",
                "spend_amount": "$10"
            }
        }
    }
    wf = Workflow(body=workflow_body)
    resp = supr_client.trigger_workflow(wf)
    print(resp)


if __name__ == "__main__":
    test_request()
