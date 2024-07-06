<p align="center">
  <img src="https://raw.githubusercontent.com/ajatkj/typed_argparser/main/assets/logo.png" alt="Description of the image">
</p>
<!--
<p align="center">
  <a href="https://github.com/ajatkj/typed_argparser/actions?query=workflow%3ATest+event%3Apush+branch%3Amain" target="_blank">
      <img src="https://img.shields.io/github/actions/workflow/status/ajatkj/typed_argparser/tests.yml?branch=main&event=push&style=flat-square&label=test&color=%2334D058" alt="Test">
  </a>
  <a href="https://app.codecov.io/gh/ajatkj/typed_argparser/tree/main/" target="_blank">
      <img src="https://img.shields.io/codecov/c/github/ajatkj/typed_argparser?color=%2334D058&style=flat-square" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/typed-argparser" target="_blank">
      <img src="https://img.shields.io/pypi/v/typed-argparser?color=%2334D058&label=pypi%20package&style=flat-square" alt="Package version">
  </a>
  <a href="https://pypi.org/project/typed-argparser" target="_blank">
      <img src="https://img.shields.io/pypi/pyversions/typed-argparser?color=%2334D058&style=flat-square" alt="Supported Python versions">
  </a>
</p> -->

# typed-argparser

typed-argparser is a python package to create command line programs by leveraging python type hints.
It uses Python's type hints to provide a convenient way of parsing and validating command line arguments.

## Features

✓ **Type Hinting:** Uses type hints to parse and validate command-line arguments.<br />
✓ **Modular Interface:** Easily define arguments and commands in a clear, organized way.<br />
✓ **Automatic Help Pages:** Generates help pages automatically, so users know how to use your CLI.<br />
✓ **Nested Commands:** Supports complex applications with any level of nested commands.<br />
✓ **File Handling:** Provides out-of-the-box support for handling files.<br />
✓ **Customizable Help Messages:** Fully customizable, giving you control over usage and help messages.<br />
✓ **Built-in Validators:** Comes with many built-in validators, such as time range and length validators.<br />
✓ **Custom Types:** You can define your own custom types to validate and convert command-line arguments.<br />

## Installation

You can install `typed_argparser` using `pip`:

```sh
pip install typed-argparser
```

## Argument Type

All built-in types are supported as argument type annotations. You can also define your own custom types.<br />
Like `argparse`, you can define your own custom types to validate and convert command-line arguments to specific types.<br />
Read more about custom types [here](#Custom-Types).

### Quickstart

| type-hint              | nargs      | input argument                                             | type                       |
| ---------------------- | ---------- | ---------------------------------------------------------- | -------------------------- |
| T                      | -          | --opt \<value>                                             | T                          |
| bool                   | -          | --opt                                                      | bool                       |
| Union[T1, T2, ..., TN] | -          | --opt \<value>                                             | T1 \| T2 \| ... \| TN      |
| Union[T, bool]         | -          | --opt                                                      | bool                       |
|                        | -          | --opt \<value>                                             | T                          |
| List[T]                | int, +, \* | --opt \<value>...                                          | [T]                        |
|                        | -          | --opt \<value1> --opt \<value2>...                         | [T]                        |
| Tuple[T1, T2, ..., TN] | N          | --opt \<value1> \<value2> ... \<valueN>                    | (T1, T2, ..., TN)          |
| Tuple[T, ...]          | N > 2      | --opt \<value1> \<value2>... \<valueN>                     | (T, ...)                   |
| Dict[K, V]             | -          | --opt \<key1=value1> --opt \<key2=value2>...               | {K: V}                     |
| List[Dict[K, V]]       | -          | --opt \<key1=value1> --opt \<key2=value2>...               | [{K: V, ...}]              |
|                        | N > 2      | --opt \<key1=value1> <key3=value3> --opt \<key2=value2>... | [{K: V, ...}, {K: V}, ...] |
| datetime               | -          | --opt \<value>                                             | datetime                   |
| date                   | -          | --opt \<value>                                             | date                       |
| time                   | -          | --opt \<value>                                             | time                       |
| Path                   | -          | --opt \<value>                                             | Path                       |
| Url                    | -          | --opt \<value>                                             | Url<sup>\*</sup>           |

\* _Url_ is a special type that allows users to provide url as a string. It is not a built-in type but a custom type.

The possibilities are endless but remember some rules:

1. Union types are resolved using the first type that matches the value. So be careful to not use `str` as the first type since everything will match a string.
1. nargs is only applicable for List and Tuple types.
1. List without nargs allows users to use the option multiple times.
1. List with nargs allows users to use multiple values (depending on nargs) for a single option.
1. Dict allows users to use the option multiple times.
1. Dict and List[Dict] behaves similar to each other except that the later supports nargs.

### Arguments to Argument Types

Some argument types allow you to pass arguments to them to customize their behavior. <br />
For example, you can pass `mode` to `Path` type to specify the mode in which the file should be opened. <br />
These values are passed using python's `Annotated` type. A special `Args` class is used to represent the arguments to the type.
For example, to pass `mode` to `Path` type, you can use `path: Annotated[Path, Args(mode="r")] = argfield(...)`.

Following tables lists all available arguments to the types.

| type              | arguments       | description                                              |
| ----------------- | --------------- | -------------------------------------------------------- |
| Path<sup>\*</sup> | mode            | mode in which the file should be opened                  |
| Path<sup>\*</sup> | buffering       | buffering for the file                                   |
| Path<sup>\*</sup> | encoding        | encoding for the file                                    |
| Path<sup>\*</sup> | errors          | errors for the file                                      |
| Path<sup>\*</sup> | newline         | newline for the file                                     |
| Date              | format          | format for the date. defaults to "%Y-%m-%d"              |
| DateTime          | format          | format for the datetime. defaults to "%Y-%m-%dT%H:%M:%S" |
| Time              | format          | format for the time. defaults to "%H:%M:%S"              |
| Url               | allowed_schemes | list of allowed schemes for the url                      |
| Url               | host_required   | whether the host is required or not                      |
| Url               | port_required   | whether the port is required or not                      |

\* All arguments to pathlib.Path are supported.

Additionally, args from `Annotated` metadata are also automatically supplied to the validators. <br />
For example, the format argument for datetime type is also suuplied to the `DateTimeRangeValidator` validator so that the validator uses the correct format.

## Usage

`examples/example1.py`

```py3
# This is a complete example and should work as is

import os
import sys
from typing import Dict, List, Optional, Tuple, Union

from typed_argparser import ArgumentClass
from typed_argparser.fields import argfield


class Example1(ArgumentClass):
    """This example shows how to use some of the basic types in typed_argparser."""

    # Positional arguments do not generate short or long options
    opt1: Union[int, str] = argfield(help="opt1 is a mandatory argument which can be an integer or a string")
    opt2: List[str] = argfield(help="opt2 is a mandatory argument and can be used multiple times")
    # Optional arguments generate only long option by default if no short option is provided
    opt3: Optional[str] = argfield(help="this is an optional argument.")
    # Use Dict type to accept multiple key value pairs
    opt4: Optional[Dict[str, int]] = argfield(help="accept key value pairs. can be used multiple times.")
    # Use Tuple type to accept exactly n no. of arguments
    opt5: Optional[Tuple[str, ...]] = argfield("-o", "--option5", nargs=4, help="accept multiple options")


cli = Example1()

"""
usage: example1 [--opt3 <value>] [--opt4 <key=value>] [-o <value1> <value2> <value3> <value4>] [--help]
                <opt1> <opt2>

description:
This example shows how to use some of the basic types in typed_argparser.

positional:
<opt1>                                             opt1 is a mandatory argument which can be an integer or a string [(int|str)]
<opt2>                                             opt2 is a mandatory argument and can be used multiple times [str]
                                                   (multiple allowed)

options:
    --opt3 <value>                                 this is an optional argument. [str]
    --opt4 <key=value>                             accept key value pairs. can be used multiple times. [str, int]
                                                   (multiple allowed)
-o, --option5 <value1> <value2> <value3> <value4>  accept multiple options [(str,...)]

miscellaneous:
    --help                                         show this help message and exit
"""

cli.parse("--opt4 abc=10 --opt4 xyz=20 --option5 a b c d 20 abc")

"""
ParsedExample1(opt1=20, opt2=['abc'], opt3=None, opt4={'abc': 10, 'xyz': 20}, opt5=('a', 'b', 'c', 'd'))
"""
print(cli)

```

Check `examples` directory for more examples. For more complex examples, check `git_cli` example.

## API Reference

This section provides an overview of the API and classes used in typed_argparser.

### ArgumentClass

`ArgumentClass` is the main class in `typed_argparser`. <br />
It is used to define the command line interface and defines how the arguments are parsed.<br />
To use `ArgumentClass`, you need to define a subclass of it and define the arguments using the `argfield` function.

#### Class Variables

All class variables are optional and can be used to customize the CLI program.

- \_\_program\_\_: The name of the CLI program.
- \_\_description\_\_:The description of the CLI program.
- \_\_epilog\_\_: The epilog of the CLI program.
- \_\_usage\_\_: The usage message of the CLI program. Overrides the default usage message.
- \_\_version\_\_: The version of the CLI program.

```py3
class CLI(ArgumentClass):
    __program__ = "ls"
    __description__ = "Lists the files in a directory."
    __version__ = "1.0.0"

    long_format: Optional[bool] = argfield("-l", "--long", help="List files in long format.")
    recursive: Optional[bool] = argfield("-r", "--recursive", help="List files recursively.")
    directory: List[str] = argfield("-d", nargs="+", help="Directory to list files in.")
```

#### Methods

- ArgumentClass.parse(args: None)<br />
  Parses the command line arguments and updates the class attributes.

- ArgumentClass.execute(immediately = True, open_files = True)<br />
  Decorator to execute a function when all positional arguments of the function are provided via CLI arguments.

### ArgumentConfig

`ArgumentConfig` is a class that holds the configuration for the `ArgumentClass`. Pass this object to the `ArgumentClass` constructor to customize the CLI program.

#### Parameters

- **show_default_in_help** (bool): Whether to show default values in help messages. Defaults to True.
- **show_none_default** (bool): Whether to show default values even if they are None. Defaults to False.
- **show_type_in_help** (bool): Whether to show argument types in help messages. Defaults to True.
- **metavar_transform** (Callable[[str], str]): Function for transforming metavar strings. This is applied after all sources of metavar have been resolved.
- **heading_transform** (Callable[[str], str]): Function for transforming heading strings.
- **add_help** (bool): Whether to include help option in the parser. Defaults to True.
- **groups_sort_order** (List[str] | None): Order in which argument groups should be sorted in help message. <br />`
  "\*" is a wildcard which signifies all groups. Defaults to ["positional", "optional", "\*", "commands", "miscellaneous"].<br />
  Note: names should be an exact match to the headings.
- **compact_usage** (bool): Whether to use compact usage message. Defaults to False.<br />
  Note: You can use `command_metavar` and `option_metavar` to change the metavar for commands and optional arguments respectively.
- **default_options_group_heading** (str): Default heading for options groups. Defaults to "options".<br />
  Note: `heading_transform` will be applied to this parameter.
- **default_positional_group_heading** (str): Default heading for positional groups. Defaults to "positional".<br />
  Note: `heading_transform` will be applied to this parameter
- **default_commands_group_heading** (str): Default heading for commands groups. Defaults to "commands".<br />
  Note: `heading_transform` will be applied to this parameter
- **default_miscellaneous_group_heading** (str): Default heading for miscellaneous groups. Defaults to "miscellaneous".<br />
  Note: `heading_transform` will be applied to this parameter
- **default_description_heading** (str | None): Default heading for descriptions. Defaults to "description". Set this to `None`
  to hide the description heading.<br />
  Note: `heading_transform` will be applied to this parameter
- **default_usage_prefix** (str): Default prefix for usage messages. Defaults to "usage: ".<br />
  Note: this value will be used as is without any transformation
- **command_metavar** (str): Metavar string for commands. Defaults to "commmand". <br />
  Note: `command_metavar` is used for both `compact_usage` and default usage generated by `ArgumentClass`. Metavar transformation `transform_metavar` is only applied for default usage. For `compact_usage`, the value is used as is.
- **option_metavar** (str): Metavar string for options. Defaults to "option".<br />
  Note: no transformation is applied to this value.
- **extra_arguments** (Literal["allow", "ignore", "error"]): Behavior for handling extra arguments. Defaults to "error".<br />
  When set to `allow` a new property `extra_fields` is added to the instance of `ArgumentClass`.
- **allow_multiple_commands** (bool) _(experimental)_: Allow multiple commands. Defaults to False.

### argfield

Returns an `ArgumentField` object, which represents an argument in the command line interface.

#### Function Arguments

- **default** (T | None): The default value for the argument. It must of the same type as the argument (defined by the type hint).
- **nargs** (int | Literal["*", "+", "?"] | None): The number of times the argument can be provided.
- **const** (T | None): A constant value for the argument. It must of the same type as the argument (defined by the type hint).
- **dest** (str | None): Specify the name of the class attribute to which the argument is assigned. Specifically used to assign multiple arguments to a single class attribute using `const`.
- **metavar** (str | None): Alternate display name for the argument in the help message.
- **aliases** (Set[str] | None): A list of alternative names for a command (not applicable for arguments).
- **validator** (ArgumentValidator | None): An optional validator for the argument. Read more about validators [here](#Validators).
- **counter** (bool | None): Whether the argument is a counter. This is used to count the number of times an argument is provided (ex. -vvv).
- **help** (str | None): A help message for the argument. Set to `SUPPRESS` to hide the argument in the help message.

### ArgumentGroup

`ArgumentGroup` is a class that represents a group of arguments in the command line interface. It is used to organize arguments into logical sections. <br />
To define a group, you need to create a subclass of `ArgumentGroup` and define the arguments using the `argfield` function.

#### Parameters

- **\_\_title\_\_** (str): The title of the group.
- **\_\_group_description\_\_** (str | None): An optional description of the group.
- **\_\_hide_title\_\_** (bool): Whether to hide the title of the group in the help message.
- **\_\_exclusive\_\_** (bool): If set to True, only one argument in the group can be provided at a time.
- **\_\_required\_\_** (bool): If set to True, at least one argument in the mutually exclusive group must be provided.

### Validators

Validators provide easy way to validate your arguments as soon as they are parsed. `typed_argparser` provides certain
built-in validators but you can as easily implement your own validators (check [Custom Validators](#Custom-Validators)).

#### LengthValidator

Validates the length of any sized argument.<br />
Parameters:

- **min** (int | None): Minimum length of the argument.
- **max** (int | None): Maximum length of the argument.

#### RangeValidator

Validates the range of a numeric argument.<br />
Parameters:

- **min** (int | float | None): Minimum value of the argument.
- **max** (int | float | None): Maximum value of the argument.

#### DateTimeRangeValidator

Validates the range of a date and time argument.<br />
Parameters:

- **min** (str | None): Minimum value of datetime argument.
- **max** (str | None): Maximum value of datetime argument.
- **format** (str | None): Datetime format. Defaults to "%Y-%m-%d" for date, "%H:%M:%S" for time and "%Y-%m-%dT%H:%M:%S" for datetime.

#### PathValidator

Validates the path argument.<br />
Parameters:

- **is_absolute** (bool | None): Whether the path is absolute or not.
- **is_dir** (bool | None): Whether the path is a directory or not.
- **is_file** (bool | None): Whether the path is a file or not.
- **exists** (bool | None): Whether the path exists or not.

#### UrlValidator

Validates the url argument.<br />
Parameters:

- **allowed_schemes** (List[str] | None): List of allowed schemes for the url.
- **host_required** (bool | None): Whether the host is required or not.
- **port_required** (bool | None): Whether the port is required or not.

#### RegexValidator

Validates the regex argument.<br />
Parameters:

- **pattern** (str | None): Regex pattern to validate the argument.

#### ConfirmationValidator

This is a special validator that asks for confirmation before proceeding with the execution of the program.<br />
Parameters:

- **message** (str | None): Message to display before asking for confirmation.
- **abort_message** (str | None): Message to display when confirmation is aborted.
- **answers** (List[str] | None): List of answers to accepted for confirmation.
- **ignore_case** (bool | None): Whether to ignore case when comparing answers. Defaults to True.

## Commands

Defining commands in `typed_argparser` is similar to defining arguments.<br />
You can create a subclass of `ArgumentClass` and define the arguments using the `argfield` function. Then use the command class as typehint for the command argument.

```py3
class InitCommand(ArgumentClass):
    quiet: Optional[bool] = argfield(
        "-q", help="Only print error and warning messages; all other output will be suppressed."
    )
    branch: Optional[Path]= argfield("--initial-branch", "-b", help="Use the specified name for the initial branch in the newly created repository.")

class Git(ArgumentClass):
    init: InitCommand = argfield(help="Initialize a new Git repository.")
```

## Advanced

### Custom Types

You can define your own custom types to validate and convert command-line arguments to specific types.

More details coming soon.

```py3

```

### Custom Validators

To define a custom validator, you need to create a subclass of `ArgumentValidator` and define the validation logic using the `validator` method.

```py3
class MyValidator(ArgumentValidator):
    def validator(self, value: str, min: Optional[int] = None, max: Optional[int] = None) -> None:
        if min and max and (len(value) < min or len(value) > max):
            raise ValidationError(f"string length should be between {min} and {max}", validator=self)
        if min and len(value) < min:
            raise ValidationError(f"string length should be greater than {min}", validator=self)
        if max and len(value) > max:
            raise ValidationError(f"string length should be less than {max}", validator=self)

    def __init__(self, min: Optional[int] = None, max: Optional[int] = None) -> None:
        if (min and max and min >= max) or (min is None and max is None):
            raise ValidatorInitError("invalid range provided", validator=self)

        super().__init__(self.validator, min=min, max=max)

# License

[MIT License](./LICENSE)

# Contribution

If you are interested in contributing to typed_argparser, please take a look at the [contributing guidelines](./CONTRIBUTING.md).
```
