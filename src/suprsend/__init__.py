"""
Integrate with SuprSend platform using python

For more information about this library, checkout the README on GitHub:
    https://github.com/suprsend/suprsend-py-sdk
For the user guide, examples and more, visit the docs page at:
    https://docs.suprsend.com/docs
"""

from .version import __version__ as __version__

__author__ = "SuprSend Developers"
__credits__ = "SuprSend"

from .sdkinstance import AppInfo as AppInfo, Suprsend as Suprsend  # noqa
from .bulk_response import BulkResponse as BulkResponse  # noqa
from .event import Event as Event  # noqa
from .workflow import Workflow as Workflow  # noqa
from .workflow_request import WorkflowTriggerRequest as WorkflowTriggerRequest  # noqa
from .subscriber_list import SubscriberListBroadcast as SubscriberListBroadcast  # noqa
from .object_edit import ObjectEdit as ObjectEdit
from .user_edit import UserEdit as UserEdit
from .users_edit_bulk import BulkUsersEdit as BulkUsersEdit

from .exception import (
    InputValueError as InputValueError,
    SuprsendAPIException as SuprsendAPIException,
    SuprsendConfigError as SuprsendConfigError,
    SuprsendError as SuprsendError,
    SuprsendValidationError as SuprsendValidationError,
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
