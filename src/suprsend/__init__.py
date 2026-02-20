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

# preventing leaks to rootLogger, so that the library user can decide what should happen.
# This sets behaviour to default silent, which is what is generally expected of a library.
# Propagate defaults to true. 
# Therefore, setting logging.basicConfig(level=logging.DEBUG) 
# would automatically give root logger access to suprsend logs due to the 
# default StreamHandler() added via logging.basicConfig
# Propagate option by default should be true, so once overwritten, these logs should flow to rootLogger.
# From where, client can then choose what to do with it.

import logging
logging.getLogger("suprsend").addHandler(logging.NullHandler())
