from suprsend import Suprsend


def test_request():
    client = Suprsend("123", "123")
    client.trigger_workflow({"avs": "123"})


if __name__ == "__main__":
    test_request()
