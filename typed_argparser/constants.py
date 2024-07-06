import sys
from argparse import ONE_OR_MORE, OPTIONAL, SUPPRESS, ZERO_OR_MORE
from enum import Enum
from typing import TYPE_CHECKING, List, Literal, Type, TypedDict, Union

__all__ = ["SUPPRESS", "OPTIONAL", "ZERO_OR_MORE", "ONE_OR_MORE"]

if TYPE_CHECKING:  # pragma: no cover
    from .fields import ArgumentField
    from .groups import _ArgumentGroup


SUBPARSER_TITLE = "__SUBPARSER__"
LITERAL_TYPE = Literal
NONE_TYPE = type(None)
TYPE_TYPE = Type

if sys.version_info >= (3, 10):  # pragma: no cover
    from types import UnionType

    UNION_TYPE = (UnionType, Union)
else:  # pragma: no cover
    UNION_TYPE = (Union,)


class ActionsEnum(str, Enum):
    STORE = "store"
    STORE_CONST = "store_const"
    STORE_TRUE = "store_true"
    STORE_FALSE = "store_false"
    APPEND = "append"
    APPEND_CONST = "append_const"
    EXTEND = "extend"
    COUNT = "count"
    HELP = "help"
    VERSION = "version"


class GroupTypeEnum(str, Enum):
    FIELD = "FIELD"
    COMMAND = "COMMAND"


class ArgumentGroupRegistryType(TypedDict):
    group: "_ArgumentGroup"
    group_type: GroupTypeEnum
    fields: List["ArgumentField"]


class ArgumentRegistryType(TypedDict):
    _OPTION_FIELDS: List["ArgumentField"]
    _POSITIONAL_FIELDS: List["ArgumentField"]
    _COMMAND_FIELDS: List["ArgumentField"]


class Empty:
    pass
