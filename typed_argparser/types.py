from _strptime import TimeRE
from datetime import date as default_date
from datetime import datetime as default_datetime
from datetime import time as default_time
from enum import Enum
from os import fsencode
from pathlib import Path as DefaultPath
from sys import stdin, stdout, version_info
from typing import (  # type: ignore
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    _GenericAlias,
    _SpecialForm,
    cast,
)
from urllib.parse import urlparse
from warnings import warn

from typing_extensions import Annotated, TypeVar, get_args, get_origin

import typed_argparser.parser as parser
import typed_argparser.utils as utils
from typed_argparser.exceptions import ArgumentError

from .constants import LITERAL_TYPE, NONE_TYPE, TYPE_TYPE, UNION_TYPE

T = TypeVar("T")


def _is_simple_type(args: Any, exclude: List[Any] = []) -> bool:
    for arg in args:
        origin = get_origin(arg)
        if origin is not None and origin not in exclude:
            return False

    return True


def _remove_none_type(types: List[Any]) -> bool:
    if NONE_TYPE in types:
        types.remove(NONE_TYPE)
        return True
    return False


def _get_args(annotation: Any) -> List[Any]:
    # Using custom get_args for Union types to preserve the order of types
    # typing.get_args uses caching which doesn't necessarily return arguments
    # in the same order in which they are defined
    if get_origin(annotation) is not Union:
        return list(get_args(annotation))
    else:
        return list(annotation.__dict__["__args__"])


def _get_types(annotation: Any) -> Any:
    origin = get_origin(annotation)
    args = list(_get_args(annotation))
    arg: Any
    if origin in UNION_TYPE:
        _remove_none_type(args)
        if len(args) == 1:
            # If only 1 argument left are removing None, we evaluate types for that and ignore Union altogether
            # Ex. For Union[List[str], None], we actually want to evaluate types for List[str]
            return _get_types(args[0])
        else:
            arg = _UnionType(types=args)
    elif origin is list:
        # For list, evaluate the type of list and store the origin as list
        # Ex. List[Union[str, int, None]] is allowed.
        # TODO: remove this error after testing.
        # The code for this exists in fields.py but has not been tested
        # if not _is_simple_type(args):
        #     raise ArgumentError(f"list must be of simple builtin types '{args}'")
        return _get_types(args[0])
    # Literal type can be used as choices here so we store the values and extract the actual type from
    # type of value.
    elif origin == LITERAL_TYPE:
        arg = annotation
    elif origin is dict:
        arg = _DictType(types=args)
    elif origin is tuple:
        # For tuples, we cannot check the types at runtime since argparse extracts single value
        # from CLI at a time (of same type) and then appends and returns a list.
        # So we will pass type=str to argparse and convert to tuple after argparse has done the parsing
        arg = _TupleType(types=args)
    else:
        arg = annotation[0] if isinstance(annotation, list) else annotation

    return arg


def _get_annotated_args(args_list: List[Any] = []) -> Dict[str, Any]:
    kwargs = {}
    args = [item for item in args_list if isinstance(item, Args)]
    for arg in args:
        kwargs.update(arg.get_kwargs())
    return kwargs


def get_types(annotation: Any, parent_origin: Optional[Any] = None) -> utils.AnnotationType:
    is_optional = False
    parent_origin = get_origin(annotation)
    parent_args = list(_get_args(annotation))
    # For Annotated fields, remove Annotated keyword and find new origin for Annotated type
    # Which is the first argument in Annotated args
    annotated_args = None
    if parent_origin is Annotated:
        annotated_args = _get_args(annotation)[1:]
        annotation = _get_args(annotation)[0]
        parent_origin = get_origin(annotation)
        parent_args = list(_get_args(annotation))

    # For Type fields, we are not interested in the "type" of type so make origin as None
    # Eg. Type[int] or Type is same for us
    if parent_origin is type:
        annotation = parent_origin
        parent_origin = None

    if parent_origin in UNION_TYPE:
        is_optional = _remove_none_type(parent_args)
        if len(parent_args) == 1:
            parent_origin = get_origin(parent_args[0])

    arg = _get_types(annotation)

    value = None
    if isinstance(arg, type) and issubclass(arg, Enum):
        value = [a.value for a in arg]
        arg = type(value[0])

    if get_origin(arg) == LITERAL_TYPE:
        value = _get_args(arg)
        arg = type(value[0])

    if arg is Any:
        arg = str

    if arg is TYPE_TYPE or get_origin(arg) is type:
        arg = type

    if arg is default_date:
        arg = _DateType

    if arg is default_datetime:
        arg = _DateTimeType

    if arg is default_time:
        arg = _TimeType

    if arg is DefaultPath:
        arg = _PathType

    # Initialise custom types with Annotated Args or without
    # any args. Going through all this trouble to have a nice
    # dynamic message with runtime properties
    # like "date [%Y-%m-%d]" instead of just "date"
    if isinstance(arg, type) and issubclass(arg, ArgumentType):
        runtime_args = {}
        if annotated_args:
            runtime_args = _get_annotated_args(annotated_args)
        arg = arg(**runtime_args) if runtime_args else arg()

    if (
        annotated_args
        and any([type(arg_) is Args for arg_ in annotated_args])
        and isinstance(arg, type)
        and issubclass(arg, parser.ArgumentClass)
    ):
        warn(f"'Args' have no meaning for subcommand {arg.__class__.__name__}", category=Warning, stacklevel=10)

    if isinstance(arg, (_GenericAlias, _SpecialForm)):
        raise ArgumentError(f"type '{arg}' not supported")

    return {"origin": parent_origin, "args": arg, "value": value, "optional": is_optional}


class Args:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def get_kwargs(self, args: Optional[List[str]] = None) -> Dict[str, Any]:
        kwargs = {}
        if args:
            for arg in args:
                if self.kwargs.get(arg, None):
                    kwargs[arg] = self.kwargs[arg]
        elif args is None:
            kwargs = self.kwargs
        else:
            pass
        return kwargs


class ArgumentType:
    def __new__(cls, value_str: Optional[str] = None, *clargs: Any, **clkwargs: Any) -> "ArgumentType":
        # Class name update added here because when _new raises error, class name is not updated dynamically
        if hasattr(cls, "help_str"):
            help_str = cls.help_str(**clkwargs)
            cls._update_class_name_dynamically(help_str)

        # new should return a tuple of args and kwargs to be sent to the super class
        if hasattr(cls, "new"):
            args, kwargs = cls.new(value_str, *clargs, **clkwargs)
            if len(cls.__bases__) == 1:
                self = super().__new__(cls)
            else:
                self = super().__new__(cls, *args, **kwargs)

            if hasattr(self, "help_str"):
                help_str = self.help_str(**clkwargs)
                self._update_instance_name_dynamically(help_str)
            return self
        else:  # pragma: no cover
            raise NotImplementedError(f"{cls.__name__} does not have 'new' method implemented")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._args = args
        self._kwargs = kwargs

    def __call__(self, value: Any) -> "ArgumentType":
        return type(self)(value, *self._args, **self._kwargs)

    @classmethod
    def _update_class_name_dynamically(cls, name: str) -> None:
        cls.__name__ = name

    def _update_instance_name_dynamically(self, name: str) -> None:
        self.__name__ = name

    def __deepcopy__(self, memo: Any) -> "ArgumentType":
        # Create a new instance with the same value
        new_instance = self.__class__(*self._args, **self._kwargs)
        return new_instance


class _PathType(ArgumentType, DefaultPath):
    _flavour = getattr(type(DefaultPath()), "_flavour")
    __metavar__ = "Path"
    __type_name__ = "Path"

    @classmethod
    def new(cls, *args: Any, **__: Any) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        if args[0] is None:
            return (), {}
        else:
            return args, {}

    def __init__(
        self,
        *args: Any,
        mode: str = "r",
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        **__: Any,
    ) -> None:
        # Make sure to send all other arguments other than the input value
        if version_info >= (3, 12):
            super(DefaultPath, self).__init__(*args)
        super().__init__(mode=mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline)
        self.mode = mode
        self.buffering = buffering
        self.encoding = encoding
        self.errors = errors
        self.newline = newline

    def open(
        self,
        mode: Optional[str] = None,
        buffering: Optional[int] = None,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
    ) -> Any:
        mode_ = mode or self.mode
        if fsencode(self.name) == b"-":
            if any(m in mode_ for m in ["w", "a", "x"]):
                return stdout
            else:  # pragma: no cover
                return stdin
        return super().open(
            mode or self.mode,
            buffering or self.buffering,
            encoding or self.encoding,
            errors or self.errors,
            newline or self.newline,
        )

    @classmethod
    def help_str(cls, **__: Any) -> str:
        return f"{getattr(cls, '__type_name__','Path')}"


class _DateType(ArgumentType, default_date):
    __metavar__ = "date"
    __type_name__ = "date"

    @classmethod
    def new(
        cls, value_str: Optional[str] = None, format: str = "%Y-%m-%d", **__: Any
    ) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        # Validate format using _strptime's TimeRE class
        try:  # pragma: no cover
            # KeyError raised when a bad format is found; can be specified as
            # \\, in which case it was a stray % but with a space after it
            TimeRE().compile(format)
        except KeyError as err:  # pragma: no cover
            bad_directive = err.args[0]
            if bad_directive == "\\":  # pragma: no cover
                bad_directive = "%"
            del err
            raise ArgumentError(f"'{bad_directive}' is a bad directive in format '{format}'") from None
        # IndexError only occurs when the format string is "%"
        except IndexError:  # pragma: no cover
            raise ArgumentError(f"stray %% in format '{format}'") from None

        if value_str:
            try:
                d_ = default_datetime.strptime(value_str, format).date()
            except ValueError:
                raise ValueError(f"date string '{value_str}' does not match '{format}'") from None
            return (d_.year, d_.month, d_.day), {}
        else:
            return (1900, 1, 1), {}

    @classmethod
    def help_str(cls, format: Optional[str] = "%Y-%m-%d", **__: Any) -> str:
        return f"{getattr(cls, '__type_name__','date')} [{format}]"


class _DateTimeType(ArgumentType, default_datetime):
    __metavar__ = "datetime"
    __type_name__ = "datetime"

    @classmethod
    def new(
        cls, value_str: Optional[str] = None, format: str = "%Y-%m-%dT%H:%M:%S", **__: Any
    ) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        # Validate format using _strptime's TimeRE class
        try:
            # KeyError raised when a bad format is found; can be specified as
            # \\, in which case it was a stray % but with a space after it
            TimeRE().compile(format)
        except KeyError as err:
            bad_directive = err.args[0]
            if bad_directive == "\\":  # pragma: no cover
                bad_directive = "%"
            del err
            raise ArgumentError(f"'{bad_directive}' is a bad directive in format '{format}'") from None
        # IndexError only occurs when the format string is "%"
        except IndexError:
            raise ArgumentError(f"stray %% in format '{format}'") from None

        if value_str:
            try:
                dt_ = default_datetime.strptime(value_str, format)
            except ValueError:
                raise ValueError(f"datetime string '{value_str}' does not match '{format}'") from None
            return (dt_.year, dt_.month, dt_.day, dt_.hour, dt_.minute, dt_.second, dt_.microsecond, dt_.tzinfo), {}
        else:
            return (1900, 1, 1, 0, 0, 0), {}

    @classmethod
    def help_str(cls, format: Optional[str] = "%Y-%m-%dT%H:%M:%S", **__: Any) -> str:
        return f"{getattr(cls, '__type_name__','datetime')} [{format}]"


class _TimeType(ArgumentType, default_time):
    __metavar__ = "time"
    __type_name__ = "time"

    @classmethod
    def new(
        cls, value_str: Optional[str] = None, format: str = "%H:%M:%S", **__: Any
    ) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        # Validate format using _strptime's TimeRE class
        try:  # pragma: no cover
            # KeyError raised when a bad format is found; can be specified as
            # \\, in which case it was a stray % but with a space after it
            TimeRE().compile(format)
        except KeyError as err:  # pragma: no cover
            bad_directive = err.args[0]
            if bad_directive == "\\":  # pragma: no cover
                bad_directive = "%"
            del err
            raise ArgumentError(f"'{bad_directive}' is a bad directive in format '{format}'") from None
        # IndexError only occurs when the format string is "%"
        except IndexError:  # pragma: no cover
            raise ArgumentError(f"stray %% in format '{format}'") from None

        if value_str:
            try:
                t_ = default_datetime.strptime(value_str, format).time()
            except ValueError:
                raise ValueError(f"time string '{value_str}' does not match '{format}'") from None
            return (t_.hour, t_.minute, t_.second, t_.microsecond, t_.tzinfo), {}
        else:
            return (0, 0, 0), {}

    @classmethod
    def help_str(cls, format: Optional[str] = "%H:%M:%S", **__: Any) -> str:
        return f"{getattr(cls, '__type_name__','time')} [{format}]"


class UrlType(ArgumentType):
    __metavar__ = "url"
    __type_name__ = "Url"

    @classmethod
    def new(cls, *args: Any, **kwargs: Any) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        return ("",), {}

    def __init__(
        self,
        url: Optional[str] = None,
        allowed_schemes: List[str] = [],
        host_required: bool = False,
        port_required: bool = False,
    ):
        # Make sure to send all other arguments other than the input value
        super().__init__(allowed_schemes=allowed_schemes, host_required=host_required, port_required=port_required)
        if not url:
            return
        if not isinstance(url, str):  # pragma: no cover
            raise ArgumentError(f"invalid url format '{type(url)}', str expected.")

        self.url = urlparse(url)

        rc = utils.validate_url(
            self.url, allowed_schemes=allowed_schemes, host_required=host_required, port_required=port_required
        )
        if rc != "":
            raise ValueError(rc)

        self.scheme = self.url.scheme
        self.host = self.url.hostname
        self.username = self.url.username
        self.password = self.url.password
        self.port = self.url.port
        self.path = self.url.path
        self.query = self.url.query
        self.fragment = self.url.fragment

    @classmethod
    def help_str(cls, allowed_schemes: List[str] = [], **__: Any) -> str:
        if allowed_schemes:
            return f"url [{'|'.join(allowed_schemes)}]"
        else:
            return "url"

    def __repr__(self) -> str:
        if hasattr(self, "url"):
            return self.url.geturl()
        else:
            return "url"


# This is a psuedo type, an object of _TupleType is not created, instead
# just type conversion is performed in __call__ method.
class _TupleType:
    # _TupleType is used internally when tuple type is specified as annotation.
    # It is not meant to be used directly as annotation for fields as fields
    # will lose their type annotations
    # __init__ method is used to initialize _TupleType class with types in
    # get_types function
    # __call__ method receives only 1 argument (list of values) which tries
    # to resolve the input list of values based on tuple types provided
    # Since argparse doesn't support tuples natively, we "call" this class
    # instance in _post_parse_conversion method

    def __init__(self, types: List[Any] = []):
        for typ in types:
            if get_origin(typ) is not None and get_origin(typ) is not type:
                raise ArgumentError(f"tuple types must be simple builtin types - '{getattr(typ, '__name__', repr(typ))}'")
        self.types = types

    def __call__(self, value: Union[str, List[str]]) -> Any:
        if isinstance(value, str):
            # This is a dummy call where _TupleType is passed as type
            # to argparse.ArgumentParser.add_arguments since it doesn't
            # support Tuple types natively
            return value

        # This is the actual conversion call from _post_parse_conversion
        if len(value) != len(self.types) and not self.has_ellipsis():  # pragma: no cover
            raise ValueError("tuple and value mismatch")
        result = []
        if not self.has_ellipsis():
            for val, typ in zip(value, self.types):
                if typ is TYPE_TYPE or get_origin(typ) is type:
                    result.append(val)
                else:
                    result.append(typ(val))
        else:
            typ = self.types[0]
            for val in value:
                if typ is TYPE_TYPE or get_origin(typ) is type:
                    result.append(val)
                else:
                    result.append(typ(val))

        return tuple(result)

    def has_ellipsis(self) -> bool:
        return Ellipsis in self.types

    # def __str__(self) -> str:
    #     if self.has_ellipsis():
    #         types = [getattr(self.types[0], "__name__", repr(self.types[0])), "..."]
    #     else:
    #         types = [getattr(t_, "__name__", repr(t_)) for t_ in self.types]
    #     return f"<class '_TupleType[{','.join(types)}]'>"

    def __repr__(self) -> str:
        if self.has_ellipsis():
            types = [getattr(self.types[0], "__name__", repr(self.types[0])), "..."]
        else:
            types = [getattr(t_, "__name__", repr(t_)) for t_ in self.types]
        return "({})".format(",".join(types))


# This is a psuedo type, an object of _UnionType is not created, instead
# just type conversion is performed in __call__ method.
class _UnionType:
    # _UnionType is used internally when union type is specified as annotation.
    # It is NOT meant to be used directly as annotation for fields as fields
    # will lose their type annotations.
    # __init__ method is used to initialize _UnionType class with types in
    # get_types function
    # __call__ method receives only 1 argument (string) which tries
    # to resolve the input string value based on union types provided.
    # The order of types in union is taken into consideration for resolving values.
    # So make sure to put "str" as the last union argument else everything will
    # get resolved as string on the first match.
    def __init__(self, types: List[Any] = [int, str]):
        # For more than 1 argument, we first check if all remaining arguments are simple built-ins
        # and then return a partial union function that best evaluates the value based on this simple union
        # Ex. Union[int, str] or Union[float, int, bool] etc.
        # Union[List[str], str] etc will raise error
        if not _is_simple_type(types):
            raise ArgumentError(f"unions must simple builtin types - '{getattr(types, '__name__', repr(types))}'")
        self.types = types

    def __call__(self, value: str) -> Any:
        for arg in self.types:
            if arg is bool:
                if value == "True" or value == "":
                    return True
                if value == "False" or value is None:
                    return False
            else:
                try:
                    return arg(value)
                except Exception:
                    continue
        # ValueError is caught in _get_values method of argpase.ArgumentParser class, so
        # the message defined here doesn't matter
        raise ValueError("union conversion error")

    def __repr__(self) -> str:
        types = [t_.__name__ for t_ in self.types]
        return "({})".format("|".join(types))


# This is a psuedo type, an object of _DictType is not created, instead
# just type conversion is performed in __call__ method.
class _DictType:
    # _DictType is used internally when dict type is specified as annotation.
    # It is NOT meant to be used directly as annotation for fields as fields
    # will lose their type annotations.
    #
    # __init__ method is used to initialize _DictType class with types in
    # get_types function
    #
    # __call__ method receives only 1 argument (string) which tries
    # to resolve the input string value based on dict type provided.
    #
    # This input string can be in the format key=value, key= or just key.
    # Last 2 formats are only applicable if the value type is a boolean or
    # union of boolean.
    #
    # Dict values are resolved using _DictType.
    def __init__(self, types: List[Any] = []):
        key_type, value_type = types
        # Only allow string and int keys for dictionary type
        if key_type not in [str, int]:
            raise ArgumentError("dictionary key type must be one of 'str' or 'int'")
        if value_type not in [str, int, float, bool, NONE_TYPE] and get_origin(value_type) not in UNION_TYPE:
            raise ArgumentError("dictionary value type must be one of 'str', 'int', 'float', 'bool', 'None' and 'Union'")
        if get_origin(value_type) in UNION_TYPE:
            if not _is_simple_type(list(get_args(value_type))):
                raise ArgumentError("unions must be simple builtin types")
        self.types = types

    def _get_dict_values(self, value: str) -> Tuple[str, Optional[Union[str, bool]]]:
        split_result = value.split("=")
        val: Optional[Union[str, bool]]
        if len(split_result) == 2:
            key, val = split_result
        elif len(split_result) == 1:
            key = split_result[0]
            val = "True"
        else:  # pragma: no cover
            # This is not raised in testing as its caught while parsing and SystemExit raised
            raise ValueError("invalid value for dictionary")
        if key == "":  # pragma: no cover
            # This is not raised in testing as its caught while parsing and SystemExit raised
            raise ValueError("invalid value (no key) for dictionary")
        return key, val if val != "" else "True"

    def __call__(self, value: Union[str, Dict[Any, Any]]) -> Dict[Any, Any]:
        if isinstance(value, str):
            key, val = self._get_dict_values(value)
        else:
            key, val = next(iter(value.items()))
        key_type = self.types[0]
        val_type = self.types[1]
        origin = get_origin(val_type)
        args = list(_get_args(val_type))
        try:
            key = key_type(key)
        except ValueError:  # pragma: no cover
            raise ArgumentError("dict key is invalid")
        if origin in UNION_TYPE:
            is_optional = _remove_none_type(args)
            if is_optional and val is None:
                computed_val = None
            else:
                computed_val = _UnionType(types=args)(cast(str, val))
        else:
            try:
                computed_val = val_type(val)
            except ValueError:
                raise ArgumentError("dict value conversion error") from None

        return {key: computed_val}

    # def __str__(self) -> str:
    #     key_t, val_t = self.types
    #     str_repr = f"{key_t.__name__}, "
    #     str_repr += str(_UnionType(_get_args(val_t))) if get_origin(val_t) is Union else val_t.__name__

    #     return f"<class '_DictType[{str_repr}]'>"

    def __repr__(self) -> str:
        key_t, val_t = self.types
        str_repr = f"{key_t.__name__}, "
        str_repr += repr(_UnionType(_get_args(val_t))) if get_origin(val_t) is Union else val_t.__name__
        return f"[{str_repr}]"
