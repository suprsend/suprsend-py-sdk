# suprsend-py-sdk

### Installation
$ pip install suprsend-py-sdk

### Usage
```python3
from suprsend import Suprsend
supr = Suprsend("env_key", "env_secret", post_url="")
workflow_params = {}
supr.execute_workflow(workflow_params)
```
