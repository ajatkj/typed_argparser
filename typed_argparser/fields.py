from enum import Enum
from pathlib import Path, PosixPath, WindowsPath
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Set, Tuple, Type, Union, cast

from typing_extensions import Annotated, Doc, get_args, get_origin

import typed_argparser.parser as parser
from typed_argparser.types import Args, ArgumentType, _DictType, _PathType, _TupleType, _UnionType

from .config import ArgumentConfig
from .constants import OPTIONAL, SUPPRESS, ActionsEnum
from .exceptions import ArgumentError
from .groups import _ArgumentGroup, arggroup
from .libs import BooleanOptionalAction
from .utils import qualified_name
from .validators import ArgumentValidator

if TYPE_CHECKING:  # pragma: no cover
    from argparse import Action


class ArgumentField:
    # Not to be used directly. An instance is created by the public function `argfield`
    # This class holds all necessary information about an ArgumentField and performs
    # various transformations and validations.

    __slots__ = (
        "default",
        "dest",
        "metavar",
        "counter",
        "aliases",
        "validator",
        "help",
        "nargs",
        "const",
        "_config",
        "_name",
        "_original_name",
        "_shortopts",
        "_longopts",
        "_required",
        "_origin",
        "_type",
        "_raw_type",
        "_action",
        "_choices",
        "_group",
        "_processed",
    )

    def __init__(
        self,
        *opts: str,
        default: Optional[Any] = None,
        help: Optional[str] = None,
        nargs: Optional[Union[int, Literal["+", "?", "*"]]] = None,
        const: Optional[Any] = None,
        dest: Optional[str] = None,
        counter: Optional[bool] = False,
        metavar: Optional[Union[str, Tuple[str, ...]]] = None,
        aliases: List[str] = [],
        validator: Optional[ArgumentValidator[Any]] = None,
    ) -> None:
        shortopts = [opt for opt in opts if opt.startswith("-") and opt[0:2] != "--"]
        longopts = [opt for opt in opts if opt.startswith("--")]
        # If opts is provided and longopts is not there then SUPPRESS long opt
        if opts and len(longopts) == 0:
            longopts = [SUPPRESS]
        self._name: Optional[str] = None
        self._original_name: Optional[str] = None
        self.default = default
        self.help = help
        self._required = False
        self._shortopts = shortopts
        self._longopts = longopts
        self._type: Optional[Any] = None
        self._origin: Optional[Any] = None
        self._raw_type: Optional[Any] = None
        self.nargs = nargs
        self._action: Optional[Union[ActionsEnum, Type["Action"]]] = ActionsEnum.STORE
        self.const = const
        self._choices: Optional[Any] = None
        self.dest = dest
        self.metavar: Optional[Union[str, Tuple[str, ...]]] = metavar
        self.counter = counter
        self._group: Optional[Union[str, _ArgumentGroup]] = None
        self.aliases = aliases
        self._config = ArgumentConfig()
        self.validator = validator
        self._processed = False

    def is_list(self) -> bool:
        return self._origin == list

    def is_tuple(self) -> bool:
        return isinstance(self._type, _TupleType)

    def is_union_w_boolean(self) -> bool:
        return isinstance(self._type, _UnionType) and bool in self._type.types

    def is_union(self) -> bool:
        return isinstance(self._type, _UnionType)

    def is_dict(self) -> bool:
        return isinstance(self._type, _DictType)

    def is_subcommand(self) -> bool:
        return isinstance(self._type, type) and issubclass(self._type, parser.ArgumentClass)

    def is_positional(self) -> bool:
        return not self._longopts and not self._shortopts

    def get_annotated_args(self, args_list: Optional[List[str]] = None) -> Dict[str, Any]:
        kwargs = {}
        if get_origin(self._raw_type) is Annotated:
            args = list(filter(lambda item: isinstance(item, Args), get_args(self._raw_type)[1:]))
            for arg in args:
                kwargs.update(arg.get_kwargs(args_list))
        return kwargs

    def get_annotated_doc(self) -> Optional[str]:
        if get_origin(self._raw_type) is Annotated:
            # Annotated supports multiple arguments. Devs might want to use Annotated for
            # other purposes, so we check if any one of the arguments is Doc and not just
            # the first one.
            args = list(get_args(self._raw_type))[1:]
            doc = next(filter(lambda item: isinstance(item, Doc), args), None)
            if isinstance(doc, Doc):
                return doc.documentation
        return None

    def get_field_name(self) -> str:
        self._name = cast(str, self._name)
        opts = self._shortopts + self._longopts
        if len(opts) > 0:
            return "/".join(opts)
        elif self.metavar and self.metavar != SUPPRESS:
            return self.metavar if isinstance(self.metavar, str) else " ".join(list(self.metavar))
        return self._name  # pragma: no cover

    def eval_name(self, name: str) -> None:
        if name.count("__") > 0:
            raise ArgumentError(f"'{name}' cannot have '__' in their name")
        self._name = name.replace("_", "", 1) if name.startswith("_") else name

    def eval_dest(self, subcommand_prefix: Optional[str] = None) -> None:
        # Generate destination name for a field. If its a subcommand field, append the
        # subcommand_prefix to the field name. This is to avoid accidentally over-writing
        # fields when they have same name across multiple subcommands.
        # Ex. Almost all git subcommands have <pathspec>.
        self._original_name = cast(str, self._original_name)
        if self._original_name.startswith("_"):
            if self.dest is None:
                raise ArgumentError("field starting with _ should have 'dest' property", field=self)
        dest = self.dest if self.dest else self._name
        if dest:
            self.dest = qualified_name(dest, qual=subcommand_prefix)

    def eval_shortopts(self, used_opts: Set[str]) -> None:
        # If shortopt is provided, use that
        # If not provided, generate shortopt 'only' if longopt is not provided and field is optional
        if self._name is None:  # pragma: no cover
            return None

        if self._shortopts:
            return

    def eval_longopts(self, used_opts: Set[str]) -> None:
        # longopt will be generated automatically if users don't provide any arguments
        # If longopt is provided, use that
        # If not provided, generate longopt for all 'optional' fields unless explicitly set as SUPPRESS
        # longopt is set to SUPPRESS when user provides only shortopt
        if self._name is None:  # pragma: no cover
            return None

        name = self._name.split("__", 1)[1] if self._name.find("__") > -1 else self._name
        if self._longopts:
            if self._longopts[0] == SUPPRESS:
                self._longopts = []
            return

        if not self._required:
            opt = "--{}".format(name.lower().replace("_", "-"))
            if opt in used_opts:
                raise ArgumentError(f"conflict in generating 'longopt'. '{opt}' already in use", self)
            self._longopts = [opt]
            return

    def eval_nargs(self) -> None:
        # This one is a bit complicated given various combinations in which type hints can be used.
        # Remember this - nargs signifies how many values can be supplied to an option while action
        #  = append signifies that option can be used multiple times. You can combine both as well.
        # Rules:
        # Rule 1: nargs is mandatory for tuple types. Whether the tuple is a top level type hint or
        # within a list.
        #   Ex. for Tuple[int, str] nargs should be 2.
        #       for List[Tuple[int,bool,str]] nargs should be 3. In this case nargs is applied to Tuple,
        #           not list (and action changed to append). With this you can use the option like:
        #               --option 10 True foo Or you can use option multiple times (since its a list)
        #               --option 10 True foo --option 20 False bar
        #       for Tuple[int, ...] or List[Tuple[int, ...] nargs can be any number greater than 2.
        # Rule 2: For Union fields with bool ex. Union[int, bool], nargs must be "?" or None.
        #       This also works for list of union fields like List[Union[int, bool]]
        #       This lets you use options like --option 10 (result option=10) or --option (result option=True)
        # Rule 3: If const is provided, nargs must be "?" or None. For ex. with const="foo"
        #       This lets you use options like --option 10 (result option=10) or --option (result option="foo")
        # Rule 4: If nargs is provided for list, it must be "+" or "*". If not provided, option can be used
        #       multiple times.
        if self.is_tuple() and isinstance(self._type, _TupleType):
            # Integer value > 1 is required for tuple types whether its a tuple in list or at parent level
            if (
                not isinstance(self.nargs, int) or (isinstance(self.nargs, int) and self.nargs < 2)
            ) and self.const is None:
                raise ArgumentError("'nargs' must be an integer value (greater than 2) for tuple fields", field=self)
            if (len(self._type.types) != self.nargs and not self._type.has_ellipsis()) and self.const is None:
                raise ArgumentError(
                    f"'nargs' ({self.nargs}) must be same as no. of fields in tuple ({len(self._type.types)})", field=self
                )
        if self.is_union_w_boolean() and (self.nargs != OPTIONAL and self.nargs is not None):
            raise ArgumentError(f"'nargs' must be '{OPTIONAL}' or 'None' for union with bool fields", field=self)
        if self.const is not None and self.nargs is not None and self.nargs != OPTIONAL and not self.is_tuple():
            raise ArgumentError(f"'nargs' must be '{OPTIONAL}' or 'None' to supply 'const'", field=self)
        if self.nargs:
            if not self.is_list() and not self.is_tuple() and self.nargs != OPTIONAL:
                raise ArgumentError("must be list or tuple type when 'nargs' is specified", field=self)
            return
        # Do not set nargs for list types. The reason
        # For list types - we use action as append and nargs as not specified. This allows users to use the argument
        # multiple times like --foo hello --foo world
        # For list types, if user wants to have multiple arguments per single command, then provide nargs explicitly
        # Ex --foo hello world will work when nargs is > 0 or + or *
        if self.const or self.is_union_w_boolean():
            self.nargs = OPTIONAL

    def eval_metavar(self) -> None:
        # Extra metavar from various sources and if not found use the defaults
        # Highest preference is metavar provided at field level (argfield)
        # Then look for metvar at custom type level. Followed by rest
        if self._processed is True:
            return
        field_name = cast(str, self._name)
        if self.metavar == SUPPRESS:
            raise ArgumentError("'metavar' property cannot be suppressed", field=self)
        # Highest preference to metavar provided at field level
        if self.metavar:
            if self.is_subcommand():
                raise ArgumentError("'metavar' property not applicable for subcommands", field=self)
        elif self._type and hasattr(self._type, "__metavar__") and not self.is_positional():
            self.metavar = self._type.__metavar__
        elif self._choices:
            self.metavar = "({})".format("|".join([str(choice) for choice in self._choices]))
        elif self.is_dict():
            self.metavar = "key=value"
        elif self.is_positional():
            self.metavar = field_name
        elif self.nargs and isinstance(self.nargs, int):
            self.metavar = tuple([f"value{i}" for i in range(1, self.nargs + 1)])
        elif self._type in [str, int, float] or self.is_union():
            self.metavar = "value"
        elif self._type is None:
            self.metavar = field_name
        else:
            # Any other arbitrary type metavar will be the type name like PATH etc.
            self.metavar = "{}".format(str(getattr(self._type, "__name__", repr(self._type)))).lower()

        # Apply metvar transformation
        if self.metavar:
            if isinstance(self.metavar, str):
                self.metavar = self._config.metavar_transform(self.metavar)
            else:
                self.metavar = tuple([self._config.metavar_transform(mv) for mv in self.metavar])

    def eval_aliases(self, aliases: Set[str]) -> None:
        # Check for duplicate command aliases across this parser
        for alias in cast(List[Any], self.aliases):
            if alias in aliases:
                raise ArgumentError(f"conflicting command alias '{alias}'", field=self)
            aliases.add(alias)

    def eval_action(self) -> None:
        # We are not allowing users to set action directly (to save them the confusion)
        # Instead we derive the action based on type hints, nargs etc.

        self._name = cast(str, self._name)
        if self._name.lower() == "help":
            self._action = ActionsEnum.HELP
            return

        if self._name.lower() == "version":
            self._action = ActionsEnum.VERSION
            return

        if self.const:
            # To cater for List[int] and where dest is different field
            if (self.is_list() and not self.is_union_w_boolean()) or (
                self._original_name and self._original_name.startswith("_")
            ):
                self._action = ActionsEnum.APPEND_CONST
            # To cater for List[Union[str, bool, int]]
            elif self.is_list() and self.is_union_w_boolean():
                self._action = ActionsEnum.APPEND
            else:
                # action "store_const" and nargs "?" are mutually exclusive
                self._action = None if self.nargs else ActionsEnum.STORE_CONST
            return

        # action "append" and nargs "*" | "+" are mutually exclusive
        # nargs will not be "?" at this point as it is taken care of in validation
        # For list of tuples, nargs defines the no. of arguments in the tuple and not
        # list. Ex. List[Tuple[int, str]] with nargs = 2 will work as
        # --option VAL1 VAL2 --option VAL3 VAL3
        if (self.is_list()) and (self.is_tuple() or not self.nargs):
            self._action = ActionsEnum.APPEND
            return

        if self.is_dict():
            self._action = ActionsEnum.APPEND
            return

        if self._type == bool:
            self._action = BooleanOptionalAction
            return

        if self.counter:
            self._action = ActionsEnum.COUNT
            return

        # Defaults to 'store' action
        self._action = ActionsEnum.STORE

    def eval_const(self) -> None:
        self._original_name = cast(str, self._original_name)
        if self._original_name.startswith("_"):
            if self.const is None:
                raise ArgumentError("field starting with _ should have 'const' property", field=self)
        if self.const is not None:
            if self._type == bool:
                raise ArgumentError("'const' property is not allowed for 'bool' type", field=self)

            if self.is_positional():
                raise ArgumentError("'const' property is not allowed for 'positional' arguments", field=self)

            if self._type != type(self.const):
                # TODO: This is a temporary condition. Remove in future and add proper validations
                if not self.is_list() and not self.is_dict() and not self.is_union() and not self.is_tuple():
                    raise ArgumentError("'const' must be of same type as field", field=self)

        if self.const is None:
            self.const = True if self.is_union_w_boolean() else None

    def eval_default(self) -> None:
        if self.default is not None and self.default != SUPPRESS:
            if self._required:
                raise ArgumentError("'default' is invalid for 'required' fields", field=self)
            if self._type and self.is_union():
                try:
                    calculated_default = self._type(self.default)
                except Exception:
                    raise ArgumentError(
                        f"'default' must be a valid type from the given union {repr(self._type)}", field=self
                    )
                if not isinstance(self.default, type(calculated_default)):
                    raise ArgumentError(
                        f"'default' must be a valid type from the given union {repr(self._type)}", field=self
                    )
            elif self._type and self.is_dict():
                try:
                    calculated_default = self._type(self.default)
                except Exception:
                    raise ArgumentError(f"'default' must be a valid dict {repr(self._type)}", field=self)
            elif self._type and self.is_tuple():
                try:
                    if self.is_list():
                        calculated_default = [self._type(d_) for d_ in self.default]
                    else:
                        calculated_default = self._type(self.default)
                except Exception:
                    raise ArgumentError(f"'default' must be a valid tuple {repr(self._type)}", field=self)
            elif self._type and issubclass(type(self._type), ArgumentType):
                if not issubclass(type(self._type), type(self.default)):
                    # pathlib.Path is special
                    if type(self._type) is _PathType and (
                        type(self.default) in [WindowsPath, PosixPath, _PathType, Path]
                        or (isinstance(self.default, str) and self.default == "-")
                    ):
                        pass
                    else:
                        raise ArgumentError(
                            f"'default' must be of same type as defined by 'type' property, '{type(self.default).__name__}' given",
                            field=self,
                        )
            elif self._type and type(self.default) != self._type and not isinstance(self.default, Enum):
                raise ArgumentError(
                    f"'default' must be of same type as defined by 'type' property, '{type(self.default).__name__}' given",
                    field=self,
                )

        if self._name == "help":
            self.default = SUPPRESS
            return

        if self.default is None:
            default = None
            if self.counter:
                default = 0
            if self._type == bool:
                default = False
            self.default = default
            return

        # default is not None at this point
        if self.is_dict():
            self.default = [self.default] if not isinstance(self.default, list) else self.default
            return

        if isinstance(self.default, Enum):
            self.default = self.default.value
            return

    def eval_help(self) -> None:
        if self._processed:
            return
        extras = []

        # Suppress help: do not show argument in help message
        if self.help == SUPPRESS:
            return

        # For arguments (not subcommands), add default and type if available
        if not self.is_subcommand():
            if self._config.show_default_in_help:
                if (self._config.show_none_default and self.default is None) or self.default is not None:
                    extras.append("(default: {})".format(self.default)) if self.default != SUPPRESS else None
            if self._config.show_type_in_help and self._type:
                types = getattr(self._type, "__name__", repr(self._type))
                types = types.replace("%", "%%")
                if types and types.startswith("[") and types.endswith("]"):
                    types = types.lstrip("[")
                    types = types.rstrip("]")
                extras.append("[{}]".format(types))
            # TODO: for now, dict for positional arguments only support a single key=value argument.
            # Change if possible to allow multiple key=value for positional arguments
            if (
                (self.is_list() and self.nargs is None)
                or (self.is_tuple() and self.is_list() and self.nargs is not None)
                or (self.is_dict() and not self.is_positional())
                or (self.is_list() and self.nargs == OPTIONAL and self.is_union_w_boolean())
            ):
                extras.append("\n(multiple allowed)")
        extra = " ".join(extras)

        # Get documentation metadata (using Annotated and Doc) if help is not available
        if self.help is None:
            self.help = self.get_annotated_doc()

        if self.help:
            self.help = "{} {}".format(self.help, extra)
        else:
            self.help = extra

    def eval_group(self) -> None:
        # We are using our own custom groups for grouping options, positional arguments
        # commands etc. If users have not put a particular option in any group, one will
        # be assigned below based on the type of option
        if self._action in [ActionsEnum.HELP, ActionsEnum.VERSION]:
            self._group = self._config.default_miscellaneous_group_heading
        elif self._group is None:
            if self.is_subcommand():
                self._group = self._config.default_commands_group_heading
            elif self.is_positional():
                self._group = self._config.default_positional_group_heading
            else:
                self._group = self._config.default_options_group_heading

        if isinstance(self._group, str):
            self._group = arggroup(self._group, description=None)

    def eval_counter(self) -> None:
        if self.counter is False:
            return
        if self._type != int and self._type != float:
            raise ArgumentError("field type must be 'int' or 'float' for counter fields", field=self)
        if self.is_list() or self.is_dict() or self.is_tuple() or self.is_union():
            raise ArgumentError("field type must be 'int' or 'float' for counter fields", field=self)

    def __repr__(self) -> str:
        fields_str = ", ".join(f"{field}={getattr(self, field)}" for field in self.__slots__ if not field.startswith("_"))
        return f"{self.__class__.__name__}({fields_str})"

    def __str__(self) -> str:
        fields_str = ", ".join(f"{field}={getattr(self, field)}" for field in self.__slots__ if not field.startswith("_"))

        return f"{self.__class__.__name__}({fields_str})"


def argfield(
    *opts: str,
    default: Optional[Any] = None,
    help: Optional[str] = None,
    nargs: Optional[Union[int, Literal["*", "+", "?"]]] = None,
    const: Optional[Any] = None,
    dest: Optional[str] = None,
    counter: Optional[bool] = False,
    metavar: Optional[str] = None,
    aliases: List[str] = [],
    validator: Optional[ArgumentValidator[Any]] = None,
) -> Any:
    return ArgumentField(
        *opts,
        default=default,
        help=help,
        nargs=nargs,
        const=const,
        dest=dest,
        counter=counter,
        metavar=metavar,
        aliases=aliases,
        validator=validator,
    )
