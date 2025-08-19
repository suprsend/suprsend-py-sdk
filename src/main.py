from suprsend import Suprsend, Workflow, Event, WorkflowTriggerRequest


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
    properties = {
        "firstName": "Suprsend",
        "lastName": "SDK TEST",
    }
    body = {
        "workflow": "unarchive-test",
        "actor": {
            "distinct_id": "0fxxx8f74-xxxx-41c5-8752-xxxcb6911fb08",
            "name": "actor_1",
            "$skip_create": True,
        },
        "recipients": [
            # notify user
            {
                "distinct_id": "0gxxx9f14-xxxx-23c5-1902-xxxcb6912ab09",
                "$email": ["abc@example.com"],
                "name": "recipient_1",
                "$preferred_language": "en",
                "$timezone": "America/New_York",
                "$skip_create": True,
            },
            # notify object
            {"object_type": "teams", "id": "finance", "$skip_create": True},
        ],
        "data": {
            "first_name": "User",
            "invoice_amount": "$5000",
            "invoice_id": "Invoice-1234",
        },
    }
    event = Event(distinct_id="ard1231", event_name="TRIGGEREVENT2", properties=properties)
    wf = Workflow(body=workflow_body)
    wfr = WorkflowTriggerRequest(body=body, tenant_id="test", idempotency_key="test2121")
    resp = supr_client.trigger_workflow(wf)
    print(resp)
    resp_wt = supr_client.workflows.trigger(wfr)
    print(resp_wt)
    resp_event = supr_client.track_event(event)
    print(resp_event)


if __name__ == "__main__":
    test_request()
