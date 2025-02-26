"""
Integrate with SuprSend platform using python

For more information about this library, checkout the README on GitHub:
    https://github.com/suprsend/suprsend-py-sdk
For the user guide, examples and more, visit the docs page at:
    https://docs.suprsend.com/docs
"""
from .version import __version__
__author__ = 'SuprSend Developers'
__credits__ = 'SuprSend'

from .sdkinstance import Suprsend           # noqa
from .bulk_response import BulkResponse     # noqa
from .event import Event                    # noqa
from .workflow import Workflow              # noqa
from .workflow_request import WorkflowTriggerRequest # noqa
from .subscriber_list import SubscriberListBroadcast      # noqa
from .object_edit import ObjectEdit
from .user_edit import UserEdit
from .users_edit_bulk import BulkUsersEdit

from .exception import (
    SuprsendError, SuprsendConfigError, SuprsendAPIException, SuprsendValidationError,
    InputValueError,
)
