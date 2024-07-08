from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, time
from enum import Enum
from io import StringIO, TextIOWrapper
from pathlib import Path, PosixPath
import sys
from textwrap import dedent
from typing import Any, Dict, List, Literal, Optional, TextIO, Tuple, Type, Union
from unittest import TestCase, main
from unittest.mock import patch

from typing_extensions import Annotated, Doc

from typed_argparser import ArgumentClass, ArgumentConfig
from typed_argparser.constants import SUPPRESS
from typed_argparser.exceptions import ArgumentError, ValidatorInitError
from typed_argparser.fields import argfield
from typed_argparser.groups import ArgumentGroup
from typed_argparser.types import Args, UrlType
from typed_argparser.validators import (
    ConfirmationValidator,
    DateTimeRangeValidator,
    LengthValidator,
    PathValidator,
    RangeValidator,
    RegexValidator,
    UrlValidator,
)


def metavar_transform(value: str) -> str:
    return f"<{value.upper()}>"


def heading_transform(value: str) -> str:
    return f"{value.upper()}:"


config = ArgumentConfig(
    metavar_transform=metavar_transform,
    default_usage_prefix="USAGE: ",
    default_description_heading="Description",
    heading_transform=heading_transform,
    command_metavar="<COMMAND>",
)


class Choices(str, Enum):
    CHOICE1 = "CHOICE1"
    CHOICE2 = "CHOICE2"
    CHOICE3 = "CHOICE3"


class TestBasics(TestCase):
    # Basic - test standard types, choices, counters, consts etc.

    def setUp(self) -> None:
        class CLI(ArgumentClass):
            """
            This is the program description.
            """

            foo: int = argfield()
            bar: Optional[str] = argfield("-b", "--bar")
            baz: Optional[Path] = argfield()
            blm: Optional[bool] = argfield()
            verbose: Optional[int] = argfield("-v", counter=True)
            cho: Optional[Choices] = argfield(default=Choices.CHOICE2)
            lit: Optional[Literal["opt1", "opt2"]] = argfield()
            num: Optional[List[Type[int]]] = argfield(const=int)
            _str: Optional[Type[str]] = argfield(const=str, dest="num")

        self.cli = CLI(config=config)

    def test_1(self) -> None:
        # Test with all arguments
        self.cli.parse("--bar foo --baz ./home --blm -vv --cho CHOICE1 --num --str --lit opt2 10")
        self.assertIsInstance(self.cli.foo, int)
        self.assertIsInstance(self.cli.bar, str)
        self.assertIsInstance(self.cli.baz, Path)
        self.assertIsInstance(self.cli.blm, bool)
        self.assertIsInstance(self.cli.verbose, int)
        self.assertIsInstance(self.cli.cho, str)  # TODO: update this to Enum type
        self.assertIsInstance(self.cli.num, list)
        self.assertIsInstance(self.cli.lit, str)
        self.assertEqual(self.cli.foo, 10)
        self.assertEqual(self.cli.bar, "foo")
        self.assertEqual(self.cli.baz, Path("./home"))
        self.assertEqual(self.cli.blm, True)
        self.assertEqual(self.cli.verbose, 2)
        self.assertEqual(self.cli.cho, "CHOICE1")
        self.assertEqual(self.cli.num, [int, str])
        self.assertEqual(self.cli.lit, "opt2")
        self.assertEqual(
            repr(self.cli),
            "ParsedCLI(foo=10, bar=foo, baz=home, blm=True, verbose=2, cho=CHOICE1, lit=opt2, num=[<class 'int'>, <class 'str'>], _str=None)",
        )

    def test_2(self) -> None:
        # Test help and usage
        self.cli.parse("10")
        self.assertIsInstance(self.cli, ArgumentClass)
        self.assertIsInstance(self.cli.foo, int)
        self.assertIsInstance(self.cli.bar, type(None))
        self.assertIsInstance(self.cli.baz, type(None))
        self.assertIsInstance(self.cli.blm, bool)
        self.assertIsInstance(self.cli.verbose, int)
        self.assertIsInstance(self.cli.cho, str)
        self.assertEqual(self.cli.foo, 10)
        self.assertEqual(self.cli.bar, None)
        self.assertEqual(self.cli.baz, None)
        self.assertEqual(self.cli.blm, False)
        self.assertEqual(self.cli.verbose, 0)
        self.assertEqual(self.cli.cho, "CHOICE2")

    def test_help(self) -> None:
        stdout = StringIO()
        usage = """\
        USAGE: cli [-b <VALUE>] [--baz <PATH>] [--blm] [-v] [--cho <(CHOICE1|CHOICE2|CHOICE3)>] [--lit <(OPT1|OPT2)>]
                   [--num] [--str] [--help]
                   <FOO>

        DESCRIPTION:
        This is the program description.

        POSITIONAL:
        <FOO>                                  [int]

        OPTIONS:
        -b, --bar <VALUE>                      [str]
            --baz <PATH>                       [Path]
            --blm  --[no-]blm                  (default: False) [bool]
        -v                                     (default: 0) [int]
            --cho <(CHOICE1|CHOICE2|CHOICE3)>  (default: CHOICE2) [str]
            --lit <(OPT1|OPT2)>                [str]
            --num                              [type]
            --str                              [type]

        MISCELLANEOUS:
            --help                             show this help message and exit
        """
        self.maxDiff = None
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_no_args(self) -> None:
        # Test with no arguments
        error_output = """\
        USAGE: cli [-b <VALUE>] [--baz <PATH>] [--blm] [-v] [--cho <(CHOICE1|CHOICE2|CHOICE3)>] [--lit <(OPT1|OPT2)>]
                   [--num] [--str] [--help]
                   <FOO>
        cli: error: the following arguments are required: <FOO>
        """
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse(" ")
        self.assertEqual(return_code.exception.code, 2)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(error_output))


class TestListAndUnions(TestCase):
    # List, unions etc.
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            foo: List[int] = argfield(nargs=2, help="List of foo's. Max 2 allowed.")
            bar: Optional[Union[int, str]] = argfield(help="Either integer or string value.")
            baz: Optional[List[Path]] = argfield(help="Provide list of paths.")
            blm: Optional[Union[bool, str]] = argfield(help="If no value specified, True assumed.")
            bam: Optional[List[Union[int, str]]] = argfield(help="List of either integer or strings.")

        self.cli = CLI(config=config)

    def test_positional_only(self) -> None:
        self.cli.parse("10 20")
        self.assertEqual(self.cli.foo, [10, 20])
        self.assertIsInstance(self.cli.foo, list)

    def test_union_options_1(self) -> None:
        self.cli.parse("10 20 --bar 10")
        self.assertEqual(self.cli.bar, 10)
        self.assertIsInstance(self.cli.bar, int)

    def test_union_options_2(self) -> None:
        self.cli.parse("10 20 --bar hello")
        self.assertEqual(self.cli.bar, "hello")
        self.assertIsInstance(self.cli.bar, str)

    def test_multiple_arguments(self) -> None:
        self.cli.parse("10 20 --baz home --baz documents --baz downloads")
        self.assertEqual(self.cli.baz, [Path("home"), Path("documents"), Path("downloads")])
        self.assertIsInstance(self.cli.baz, list)

    def test_union_w_bool_1(self) -> None:
        self.cli.parse("10 20 --blm")
        self.assertEqual(self.cli.blm, True)
        self.assertIsInstance(self.cli.blm, bool)

    def test_union_w_bool_2(self) -> None:
        self.cli.parse("10 20 --blm hello")
        self.assertEqual(self.cli.blm, "hello")
        self.assertIsInstance(self.cli.blm, str)

    def test_list(self) -> None:
        self.cli.parse("10 20 --bam 10 --bam hello")
        if self.cli.bam:
            self.assertIsInstance(self.cli.bam, list)
            self.assertIsInstance(self.cli.bam[0], int)
            self.assertIsInstance(self.cli.bam[1], str)
            self.assertEqual(self.cli.bam, [10, "hello"])

    def test_help(self) -> None:
        stdout = StringIO()
        usage = """\
        USAGE: cli [--bar <VALUE>] [--baz <PATH>] [--blm [<VALUE>]] [--bam <VALUE>] [--help] <FOO> <FOO>

        POSITIONAL:
        <FOO>                List of foo's. Max 2 allowed. [int]

        OPTIONS:
            --bar <VALUE>    Either integer or string value. [(int|str)]
            --baz <PATH>     Provide list of paths. [Path]
                             (multiple allowed)
            --blm [<VALUE>]  If no value specified, True assumed. [(str|bool)]
            --bam <VALUE>    List of either integer or strings. [(int|str)]
                             (multiple allowed)

        MISCELLANEOUS:
            --help           show this help message and exit
        """
        self.maxDiff = None
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_union_complex_types(self) -> None:
        class CLI(ArgumentClass):
            opt1: Union[str, Dict[str, str]] = argfield()

        with self.assertRaisesRegex(
            ArgumentError, "unions must simple builtin types - '\[<class 'str'>, typing.Dict\[str, str\]\]'"
        ):
            CLI()


class TestDicts(TestCase):
    # Dicts, dicts with union etc.
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            foo: Dict[str, int] = argfield(help="Give key=value for foo.")
            bar: Optional[Dict[str, int]] = argfield(
                help="Give key=value for bar. Multiple options allowed.", default={"hello": 25}
            )
            baz: Optional[Dict[str, Union[int, bool]]] = argfield(help="Use int if int present else bool.")
            bla: Optional[List[Dict[str, str]]] = argfield(nargs=2)
            bam: Optional[int] = argfield(help=SUPPRESS)

        self.cli = CLI(config=config)

    def test_dict_1(self) -> None:
        self.cli.parse(
            "hello=1 --bar world=2 --bar universe=3 --baz abc --baz xyz=10 --baz hjk= --baz env=False --bla foo=bar bar=foo"
        )
        self.assertIsInstance(self.cli.foo, dict)
        self.assertIsInstance(self.cli.bar, dict)
        self.assertIsInstance(self.cli.baz, dict)
        self.assertEqual(self.cli.foo, {"hello": 1})
        self.assertEqual(self.cli.bar, {"hello": 25, "world": 2, "universe": 3})
        self.assertEqual(self.cli.baz, {"abc": True, "xyz": 10, "hjk": True, "env": False})
        self.assertEqual(self.cli.bla, [{"foo": "bar", "bar": "foo"}])

    def test_dict_invalid_value(self) -> None:
        error = "cli: error: argument <KEY=VALUE>: invalid [str, int] value: 'hello=20.2'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("hello=20.2")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout, line_no=2), error)

    def test_dict_1_invalid_key(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "dictionary key type must be one of 'str' or 'int'"):

            class CLI_1(ArgumentClass):
                foo: Dict[bool, int] = argfield()

            CLI_1()

    def test_dict_1_invalid_values(self) -> None:
        with self.assertRaisesRegex(
            ArgumentError, "dictionary value type must be one of 'str', 'int', 'float', 'bool', 'None' and 'Union'"
        ):

            class CLI_1(ArgumentClass):
                foo: Dict[str, Path] = argfield()

            CLI_1()

    def test_dict_1_invalid_values_union(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "unions must be simple builtin types"):

            class CLI_1(ArgumentClass):
                foo: Dict[str, Union[str, List[Path]]] = argfield()

            CLI_1()

    def test_usage(self) -> None:
        stdout = StringIO()
        usage = """\
        USAGE: cli [--bar <KEY=VALUE>] [--baz <KEY=VALUE>] [--bla <KEY=VALUE> <KEY=VALUE>] [--bam <VALUE>] [--help]
                   <KEY=VALUE>

        POSITIONAL:
        <KEY=VALUE>                        Give key=value for foo. [str, int]

        OPTIONS:
            --bar <KEY=VALUE>              Give key=value for bar. Multiple options allowed. (default: [{'hello': 25}]) [str, int]
                                           (multiple allowed)
            --baz <KEY=VALUE>              Use int if int present else bool. [str, (int|bool)]
                                           (multiple allowed)
            --bla <KEY=VALUE> <KEY=VALUE>  [str, str]
                                           (multiple allowed)

        MISCELLANEOUS:
            --help                         show this help message and exit
        """
        self.maxDiff = None
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))


class TestTuple(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[Tuple[int, str, bool]] = argfield(nargs=3, help="Add opt1")
            opt2: Optional[List[Tuple[int, int]]] = argfield(nargs=2, help="Add opt2")
            opt3: Optional[Tuple[str, ...]] = argfield(nargs=2, help="Add opt3")

        self.cli = CLI(config=config)

    def test_tuple_help(self) -> None:
        usage = """\
            USAGE: cli [--opt1 <VALUE1> <VALUE2> <VALUE3>] [--opt2 <VALUE1> <VALUE2>] [--opt3 <VALUE1> <VALUE2>] [--help]

            OPTIONS:
                --opt1 <VALUE1> <VALUE2> <VALUE3>  Add opt1 [(int,str,bool)]
                --opt2 <VALUE1> <VALUE2>           Add opt2 [(int,int)]
                                                   (multiple allowed)
                --opt3 <VALUE1> <VALUE2>           Add opt3 [(str,...)]

            MISCELLANEOUS:
                --help                             show this help message and exit
        """
        stdout = StringIO()

        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_tuple_1(self) -> None:
        self.cli.parse("--opt1 10 foo False")
        if self.cli.opt1:
            self.assertIsInstance(self.cli.opt1, tuple)
            self.assertIsInstance(self.cli.opt1[0], int)
            self.assertIsInstance(self.cli.opt1[1], str)
            self.assertIsInstance(self.cli.opt1[2], bool)

    def tests_tuple_2(self) -> None:
        self.cli.parse("--opt2 10 20 --opt2 30 40")
        if self.cli.opt2:
            self.assertIsInstance(self.cli.opt2, list)
            self.assertIsInstance(self.cli.opt2[0], tuple)
            self.assertIsInstance(self.cli.opt2[1], tuple)
            self.assertIsInstance(self.cli.opt2[0][0], int)
            self.assertIsInstance(self.cli.opt2[0][1], int)

    def test_tuple_3(self) -> None:
        self.cli.parse("--opt3 foo bar")
        if self.cli.opt3:
            self.assertIsInstance(self.cli.opt3, tuple)
            self.assertIsInstance(self.cli.opt3[0], str)
            self.assertIsInstance(self.cli.opt3[1], str)

    def test_tuple_invalid_value_1(self) -> None:
        error = "cli: error: invalid tuple [(int,str,bool)] value '20.2 foo False'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 20.2 foo False")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), error)

    def test_tuple_invalid_value_2(self) -> None:
        error = "cli: error: invalid tuple [(int,int)] value '20.2 10'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt2 20.2 10")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), error)

    def test_tuple_complex_types(self) -> None:
        class CLI(ArgumentClass):
            opt1: Tuple[str, Dict[str, str]] = argfield(nargs=2)

        with self.assertRaisesRegex(ArgumentError, "tuple types must be simple builtin types - .*Dict.*"):
            CLI()


class TestGroupsAndCommands(TestCase):
    # Groups, inherited commands and subcommands etc.
    def setUp(self) -> None:
        class RemoteAddCommand(ArgumentClass):
            source: Optional[Path] = argfield(help="Source file")
            destination: Optional[Path] = argfield(help="Destination file")

        class RemoteCommand(ArgumentClass):
            add: RemoteAddCommand = argfield(help="Add a new remote")
            branch: Optional[str] = argfield(help="Remote branch name")

        class MoveCommand(ArgumentClass):
            source: List[Path] = argfield(help="Move file/directory", nargs="+")
            dest: Path = argfield(help="Move file/directory")

        class RemoveCommand(ArgumentClass):
            source: List[Path] = argfield(help="Remove file/directory", nargs="+")

        class Group1(ArgumentGroup):
            __title__ = "group 1"
            __group_description__ = "All arguments related to group 1"

            bar: Optional[int] = argfield(help="Integer value")
            bam: Optional[float] = argfield(help="Float value")

        class Group2(ArgumentGroup):
            __title__ = "group 2"
            hug: Optional[str] = argfield(help="String value")
            puh: Optional[str] = argfield(help="String value")

        class FileCommandGroup(ArgumentGroup):
            __title__ = "file commands"
            __group_description__ = "File manipulation commands"
            __hide_title__ = True
            fmv: MoveCommand = argfield(help="Baz command for you.", aliases=["gmv"])
            frm: RemoveCommand = argfield(help="Zab command for you.")

        class DirectoryCommandGroup(ArgumentGroup):
            __title__ = "directory commands"
            __group_description__ = "Directory manipulation commands"
            __hide_title__ = True

            dmv: MoveCommand = argfield(help="Baz command for you.")
            drm: RemoveCommand = argfield(help="Zab command for you.")

        class CLI(DirectoryCommandGroup, FileCommandGroup, Group2, Group1, ArgumentClass):
            remote: RemoteCommand = argfield(help="Manipuate remote")

        self.cli = CLI(config=config)

    def test_1(self) -> None:
        self.cli.parse("--bar 2 --bam 3.0 --hug hello --puh world")
        self.assertIsInstance(self.cli.bar, int)
        self.assertEqual(self.cli.bar, 2)
        self.assertEqual(
            repr(self.cli),
            "ParsedCLI(bar=2, bam=3.0, hug=hello, puh=world, fmv=ParsedMoveCommand(source=None, dest=None), frm=ParsedRemoveCommand(source=None), dmv=ParsedMoveCommand(source=None, dest=None), drm=ParsedRemoveCommand(source=None), remote=ParsedRemoteCommand(branch=None, add=ParsedRemoteAddCommand(source=None, destination=None)))",
        )

    def test_subcommand(self) -> None:
        self.cli.parse("fmv ./home/file1 ./home/file2 ./downloads")
        self.maxDiff = None
        self.assertIsInstance(self.cli.fmv.source, list)
        self.assertIsInstance(self.cli.fmv.source[0], Path)
        self.assertIsInstance(self.cli.fmv.dest, Path)
        self.assertEqual(self.cli.fmv.source, [PosixPath("home/file1"), PosixPath("home/file2")])
        self.assertEqual(self.cli.fmv.dest, PosixPath("downloads"))
        self.assertEqual(
            repr(self.cli),
            "ParsedCLI(bar=None, bam=None, hug=None, puh=None, fmv=ParsedMoveCommand(source=[Path('home/file1'), Path('home/file2')], dest=downloads), frm=ParsedRemoveCommand(source=None), dmv=ParsedMoveCommand(source=None, dest=None), drm=ParsedRemoveCommand(source=None), remote=ParsedRemoteCommand(branch=None, add=ParsedRemoteAddCommand(source=None, destination=None)))",
        )

    def test_default_decorator(self) -> None:
        self.cli.parse("remote")
        stdout = StringIO()
        with redirect_stdout(stdout):

            @self.cli.remote.execute
            def show_origin() -> None:
                print("origin")

        self.assertEqual(stdout.getvalue(), "origin\n")

    def test_default_decorator_for_nested_command(self) -> None:
        usage = """\
        USAGE: cli remote add [--source <PATH>] [--destination <PATH>] [--help]

        OPTIONS:
            --source <PATH>       Source file [Path]
            --destination <PATH>  Destination file [Path]

        MISCELLANEOUS:
            --help                show this help message and exit
        """
        self.cli.parse("remote add")
        stdout = StringIO()
        with redirect_stdout(stdout):

            @self.cli.remote.add.execute
            def show_add_help() -> None:
                self.cli.remote.add.print_help()

        self.assertEqual(stdout.getvalue(), dedent(usage))

    def test_decorator_action(self) -> None:
        self.cli.parse("remote add --source source_file --destination destination_path")
        stdout = StringIO()
        with redirect_stdout(stdout):

            @self.cli.remote.add.execute(open_files=False)
            def show_origin(source: Path, destination: Path) -> None:
                print(f"adding {source} to {destination}")

        self.assertEqual(stdout.getvalue(), "adding source_file to destination_path\n")

    def test_help(self) -> None:
        stdout = StringIO()
        usage = """\
        USAGE: cli [--bar <VALUE>] [--bam <VALUE>] [--hug <VALUE>] [--puh <VALUE>] [--help] <COMMAND> ...

        GROUP 1:
        All arguments related to group 1

            --bar <VALUE>  Integer value [int]
            --bam <VALUE>  Float value [float]

        GROUP 2:
            --hug <VALUE>  String value [str]
            --puh <VALUE>  String value [str]

        File manipulation commands

        fmv (gmv)          Baz command for you.
        frm                Zab command for you.

        Directory manipulation commands

        dmv                Baz command for you.
        drm                Zab command for you.

        COMMANDS:
        remote             Manipuate remote

        MISCELLANEOUS:
            --help         show this help message and exit
        """
        self.maxDiff = None
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_help_for_command(self) -> None:
        stdout = StringIO()
        usage = """\
        USAGE: cli fmv [--help] <SOURCE> [<SOURCE> ...] <DEST>

        POSITIONAL:
        <SOURCE>    Move file/directory [Path]
        <DEST>      Move file/directory [Path]

        MISCELLANEOUS:
            --help  show this help message and exit
        """
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("fmv --help")

        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_common_fields(self) -> None:
        class Common(ArgumentClass):
            source: Path = argfield()
            destination: Path = argfield()

        class Command1(Common):
            pass

        class Command2(Common):
            pass

        class CLI_(ArgumentClass):
            command1: Command1 = argfield(help="Command 1 help")
            command2: Command2 = argfield(help="Command 2 help")

        cli_ = CLI_(config=config)

        usage = """\
        USAGE: cli_ command1 [--help] <SOURCE> <DESTINATION>

        POSITIONAL:
        <SOURCE>       [Path]
        <DESTINATION>  [Path]

        MISCELLANEOUS:
            --help     show this help message and exit
        """

        stdout = StringIO()

        with self.assertRaises(SystemExit) as return_coode, redirect_stdout(stdout):
            cli_.parse("command1 --help")

        self.assertEqual(return_coode.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_mutually_exclusive_group_invalid(self) -> None:
        class Group(ArgumentGroup):
            __title__ = "Foo"
            __required__ = True

            opt1: str = argfield()
            opt2: str = argfield()

        class CLI(Group, ArgumentClass):
            pass

        with self.assertRaisesRegex(
            ArgumentError, "'required' flag is only applicable when 'mutually_exclusive' is True"
        ):
            CLI()

    def test_mutually_exclusive_group(self) -> None:
        class Group(ArgumentGroup):
            __title__ = "Bar"
            __exclusive__ = True
            opt1: Optional[str] = argfield()
            opt2: Optional[str] = argfield()

        class CLI(Group, ArgumentClass):
            pass

        cli = CLI()
        stderr = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stderr):
            cli.parse("--opt1 foo --opt2 bar")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stderr), "cli: error: argument --opt2: not allowed with argument --opt1")

    def test_mixed_group(self) -> None:
        class Command(ArgumentClass):
            opt1: str = argfield()

        class Group(ArgumentGroup):
            __title__ = "Bar1"
            opt1: Optional[str] = argfield()
            opt2: Optional[str] = argfield()
            command: Command = argfield()

        class CLI(Group, ArgumentClass):
            pass

        with self.assertRaisesRegex(ArgumentError, "'command' - cannot have mixed groups of commands & fields"):
            CLI()


class TestAnnotatedAndDocs(TestCase):
    # Test help, usage, annotated, doc etc.
    def test_custom_usage(self) -> None:
        class CLI(ArgumentClass):
            __usage__ = "cli [options]... [commands]..."
            foo: Optional[int] = argfield()
            bar: Optional[str] = argfield()

        usage = """\
        USAGE: cli [options]... [commands]...

        OPTIONS:
            --foo <VALUE>  [int]
            --bar <VALUE>  [str]

        MISCELLANEOUS:
            --help         show this help message and exit
        """
        cli = CLI(config=config)
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_annotated_doc_in_help(self) -> None:
        class CLI(ArgumentClass):
            __usage__ = "cli [options]... [commands]..."
            foo: Annotated[Optional[int], Doc("Run the foo function")] = argfield()
            bar: Annotated[Optional[str], Doc("Run the bar function")] = argfield()

        usage = """\
        USAGE: cli [options]... [commands]...

        OPTIONS:
            --foo <VALUE>  Run the foo function [int]
            --bar <VALUE>  Run the bar function [str]

        MISCELLANEOUS:
            --help         show this help message and exit
        """
        cli = CLI(config=config)
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_description_docstring_in_help(self) -> None:
        class CLI(ArgumentClass):
            """
            This docstring is also used as CLI description. You can cut off the description
            using line-feed character. Anything after line-feed will not appear in program
            description.

            You can also reset formatting if you use a null character at the end of the
            description.

            Links like http://www.google.com will automatically underlined.\f

            This will not be part of the CLI description.
            """

            __usage__ = "cli [options]... [commands]..."
            __program__ = "cli-cmd"
            foo: Annotated[Optional[int], Doc("Run the foo function")] = argfield()
            bar: Annotated[Optional[str], Doc("Run the bar function")] = argfield()

        usage = """\
        USAGE: cli [options]... [commands]...

        DESCRIPTION:
        This docstring is also used as CLI description. You can cut off the description
        using line-feed character. Anything after line-feed will not appear in program
        description.

        You can also reset formatting if you use a null character at the end of the
        description.

        Links like \033[4mhttp://www.google.com\033[0m will automatically underlined.

        OPTIONS:
            --foo <VALUE>  Run the foo function [int]
            --bar <VALUE>  Run the bar function [str]

        MISCELLANEOUS:
            --help         show this help message and exit
        """
        self.maxDiff = None
        cli = CLI(config=config)
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))

    def test_description_unformatted_docstring_in_help(self) -> None:
        class CLI(ArgumentClass):
            """

            This docstring is also used as CLI description. You can cut off the description
            using line-feed character. Anything after line-feed will not appear in program
            description.

            You can also reset formatting if you use a null character at the end of the
            description.

            Links like http://www.google.com will automatically underlined.\0\f

            This will not be part of the CLI description.
            """

            __program__ = "cli-cmd"
            foo: Annotated[Optional[int], Doc("Run the foo function")] = argfield()
            bar: Annotated[Optional[str], Doc("Run the bar function")] = argfield()

        usage = """\
        USAGE: cli-cmd [--foo <VALUE>] [--bar <VALUE>] [--help]

        DESCRIPTION:
        This docstring is also used as CLI description. You can cut off the description using line-feed character.
        Anything after line-feed will not appear in program description. You can also reset formatting if you use a
        null character at the end of the description. Links like \033[4mhttp://www.google.com\033[0m will automatically
        underlined.

        OPTIONS:
            --foo <VALUE>  Run the foo function [int]
            --bar <VALUE>  Run the bar function [str]

        MISCELLANEOUS:
            --help         show this help message and exit
        """
        self.maxDiff = None
        cli = CLI(config=config)
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))


class TestRangeValidator(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            opt1: int = argfield(validator=RangeValidator(min=10, max=20))
            opt2: int = argfield(validator=RangeValidator(min=10))
            opt3: int = argfield(validator=RangeValidator(max=20))

        self.cli = CLI(config=config)

    def test_int_range_validator(self) -> None:
        self.cli.parse("10 20 19")
        self.assertEqual(self.cli.opt1, 10)
        self.assertEqual(self.cli.opt2, 20)
        self.assertEqual(self.cli.opt3, 19)

    def test_int_between(self) -> None:
        error = "cli: error: argument <OPT1>: value should be between 10 and 20"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("21 20 19")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_int_greater_than(self) -> None:
        error = "cli: error: argument <OPT2>: value should be greater than 10"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("20 2 19")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_int_less_than(self) -> None:
        error = "cli: error: argument <OPT3>: value should be less than 20"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("20 20 29")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_int_validation_init_error(self) -> None:
        with self.assertRaisesRegex(ValidatorInitError, "invalid range provided"):

            class CLI(ArgumentClass):
                opt1: int = argfield(validator=RangeValidator(min=10, max=5))


class TestDateTime(TestCase):
    # Test datetime types and validators
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            dt1: Annotated[Optional[datetime], Args(format="%Y.%m.%dT%H%M%S")] = argfield(
                validator=DateTimeRangeValidator(min="2020.01.01T123000", max="2020.02.01T123000")
            )
            dt2: Annotated[Optional[datetime], Args(format="%Y.%m.%dT%H%M%S")] = argfield(
                validator=DateTimeRangeValidator(min="2020.01.01T123000")
            )
            dt3: Annotated[Optional[datetime], Args(format="%Y.%m.%dT%H%M%S")] = argfield(
                validator=DateTimeRangeValidator(max="2020.02.01T123000")
            )

        self.cli = CLI(config=config)

    def test_datetime_range_validator(self) -> None:
        self.cli.parse("--dt1 2020.01.15T113000 --dt2 2022.01.02T113000 --dt3 2019.01.01T123000")
        self.assertEqual(self.cli.dt1, datetime(2020, 1, 15, 11, 30))
        self.assertEqual(self.cli.dt2, datetime(2022, 1, 2, 11, 30))
        self.assertEqual(self.cli.dt3, datetime(2019, 1, 1, 12, 30))

    def test_datetime_invalid_format(self) -> None:
        error = "cli: error: argument --dt1: invalid datetime [%Y.%m.%dT%H%M%S] value: '2020.01.15'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt1 2020.01.15")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_datetime_between(self) -> None:
        error = "cli: error: argument --dt1: should be between 2020-01-01 12:30:00 and 2020-02-01 12:30:00"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt1 2020.02.02T123000")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_datetime_after(self) -> None:
        error = "cli: error: argument --dt2: should be after 2020-01-01 12:30:00"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt2 2019.02.02T123000")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_datetime_before(self) -> None:
        error = "cli: error: argument --dt3: should be before 2020-02-01 12:30:00"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt3 2023.02.02T123000")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_datetime_validator_init_err(self) -> None:
        with self.assertRaisesRegex(ValidatorInitError, "invalid range provided"):

            class CLI(ArgumentClass):
                opt1: datetime = argfield(validator=DateTimeRangeValidator())

        with self.assertRaisesRegex(ValidatorInitError, "invalid format provided for min"):

            class CLI1(ArgumentClass):
                opt1: datetime = argfield(validator=DateTimeRangeValidator(min=datetime(2020, 1, 1)))  # type: ignore

        with self.assertRaisesRegex(ValidatorInitError, "invalid format provided for max"):

            class CLI2(ArgumentClass):
                opt1: datetime = argfield(validator=DateTimeRangeValidator(max=datetime(2020, 1, 1)))  # type: ignore

    def test_datetime_invalid_format_string(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'k' is a bad directive in format '%k.%m.%d'"):

            class CLI(ArgumentClass):
                opt1: Annotated[datetime, Args(format="%k.%m.%d")] = argfield()

            CLI()

    def test_datetime_invalid_format_string_extra(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "stray %% in format '%'"):

            class CLI(ArgumentClass):
                opt1: Annotated[datetime, Args(format="%")] = argfield()

            CLI()

    def test_datetime_invalid_format_string_in_validator(self) -> None:
        with self.assertRaisesRegex(
            ValidatorInitError, "DateTimeRangeValidator - 'k' is a bad directive in format '%k.%m.%d'"
        ):

            class CLI(ArgumentClass):
                opt1: datetime = argfield(validator=DateTimeRangeValidator(min="2020-1-1", format="%k.%m.%d"))

            CLI()

    def test_datetime_invalid_format_string_in_validator_extra(self) -> None:
        with self.assertRaisesRegex(ValidatorInitError, "DateTimeRangeValidator - stray %% in format '%'"):

            class CLI(ArgumentClass):
                opt1: datetime = argfield(validator=DateTimeRangeValidator(min="2020-1-1", format="%"))

            CLI()

    def test_datetime_help(self) -> None:
        usage = """\
            USAGE: cli [--dt1 <DATETIME>] [--dt2 <DATETIME>] [--dt3 <DATETIME>] [--help]

            OPTIONS:
                --dt1 <DATETIME>  [datetime [%Y.%m.%dT%H%M%S]]
                --dt2 <DATETIME>  [datetime [%Y.%m.%dT%H%M%S]]
                --dt3 <DATETIME>  [datetime [%Y.%m.%dT%H%M%S]]

            MISCELLANEOUS:
                --help            show this help message and exit
        """
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))


class TestDate(TestCase):
    # Test date types and validators
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            dt1: Annotated[Optional[date], Args(format="%Y.%m.%d")] = argfield(
                validator=DateTimeRangeValidator(min="2020.01.01", max="2020.02.01")
            )
            dt2: Annotated[Optional[date], Args(format="%Y.%m.%d")] = argfield(
                validator=DateTimeRangeValidator(min="2020.01.01")
            )
            dt3: Annotated[Optional[date], Args(format="%Y.%m.%d")] = argfield(
                validator=DateTimeRangeValidator(max="2020.02.01")
            )

        self.cli = CLI(config=config)

    def test_date_range_validator(self) -> None:
        self.cli.parse("--dt1 2020.01.15 --dt2 2022.01.02 --dt3 2019.01.01")
        self.assertEqual(self.cli.dt1, date(2020, 1, 15))
        self.assertEqual(self.cli.dt2, date(2022, 1, 2))
        self.assertEqual(self.cli.dt3, date(2019, 1, 1))

    def test_date_invalid_format(self) -> None:
        error = "cli: error: argument --dt1: invalid date [%Y.%m.%d] value: '2020.01.15T123000'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt1 2020.01.15T123000")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_date_between(self) -> None:
        error = "cli: error: argument --dt1: should be between 2020-01-01 and 2020-02-01"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt1 2020.02.02")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_date_after(self) -> None:
        error = "cli: error: argument --dt2: should be after 2020-01-01"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt2 2019.02.02")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_date_before(self) -> None:
        error = "cli: error: argument --dt3: should be before 2020-02-01"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt3 2023.02.02")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_help(self) -> None:
        usage = """\
            USAGE: cli [--dt1 <DATE>] [--dt2 <DATE>] [--dt3 <DATE>] [--help]

            OPTIONS:
                --dt1 <DATE>  [date [%Y.%m.%d]]
                --dt2 <DATE>  [date [%Y.%m.%d]]
                --dt3 <DATE>  [date [%Y.%m.%d]]

            MISCELLANEOUS:
                --help        show this help message and exit
        """
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))


class TestTime(TestCase):
    # Test time types and validators
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            dt1: Annotated[Optional[time], Args(format="%H:%M")] = argfield(
                validator=DateTimeRangeValidator(min="12:30", max="13:30")
            )
            dt2: Annotated[Optional[time], Args(format="%H:%M")] = argfield(validator=DateTimeRangeValidator(min="12:30"))
            dt3: Annotated[Optional[time], Args(format="%H:%M")] = argfield(validator=DateTimeRangeValidator(max="13:30"))

        self.cli = CLI(config=config)

    def test_time_range_validator(self) -> None:
        self.cli.parse("--dt1 12:31 --dt2 14:30 --dt3 10:00")
        self.assertEqual(self.cli.dt1, time(12, 31))
        self.assertEqual(self.cli.dt2, time(14, 30))
        self.assertEqual(self.cli.dt3, time(10, 0))

    def test_time_invalid_format(self) -> None:
        error = "cli: error: argument --dt1: invalid time [%H:%M] value: '2020.01.15T123000'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt1 2020.01.15T123000")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_time_between(self) -> None:
        error = "cli: error: argument --dt1: should be between 12:30:00 and 13:30:00"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt1 11:30")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_time_after(self) -> None:
        error = "cli: error: argument --dt2: should be after 12:30:00"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt2 12:29")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_time_before(self) -> None:
        error = "cli: error: argument --dt3: should be before 13:30:00"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--dt3 13:31")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_help(self) -> None:
        usage = """\
            USAGE: cli [--dt1 <TIME>] [--dt2 <TIME>] [--dt3 <TIME>] [--help]

            OPTIONS:
                --dt1 <TIME>  [time [%H:%M]]
                --dt2 <TIME>  [time [%H:%M]]
                --dt3 <TIME>  [time [%H:%M]]

            MISCELLANEOUS:
                --help        show this help message and exit
        """
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            self.cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))


class TestPath(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            infile: Path = argfield(validator=PathValidator(is_file=True))
            outfile: Optional[Path] = argfield(default=Path("output.txt"))
            outdir: Optional[Path] = argfield(validator=PathValidator(is_dir=True))
            indir: Optional[Path] = argfield(validator=PathValidator(exists=True))
            absdir: Optional[Path] = argfield(validator=PathValidator(is_absolute=True))
            strpath: Optional[str] = argfield(validator=PathValidator(is_dir=True))
            boolpath: Optional[bool] = argfield(validator=PathValidator(is_file=True))
            # invval: Optional[Path] = argfield(validator=PathValidator(is_dir=True, is_file=True))

        with open("/tmp/tmp.1.out", "w") as fp:
            fp.write("test")

        self.cli = CLI(config=config)

    def test_path_args(self) -> None:
        self.cli.parse("pyproject.toml --outfile output.csv --outdir tests --absdir=/tmp/tmp.1.out")

        self.assertIsInstance(self.cli.infile, Path)
        self.assertEqual(self.cli.infile, Path("pyproject.toml"))

    def test_path_invalid_file(self) -> None:
        error = "cli: error: argument <INFILE>: 'pyproject1.toml' is not a valid file"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("pyproject1.toml")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout, line_no=3), dedent(error))

    def test_path_invalid_dir(self) -> None:
        error = "cli: error: argument --outdir: 'tests1' is not a valid directory"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("pyproject.toml --outdir tests1")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout, line_no=3), dedent(error))

    def test_path_not_exist(self) -> None:
        error = "cli: error: argument --indir: 'tests12' does not exist"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("pyproject.toml --indir tests12")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout, line_no=3), dedent(error))

    def test_path_not_absolute(self) -> None:
        error = "cli: error: argument --absdir: 'tests' is not an absolute path"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("pyproject.toml --absdir tests")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout, line_no=3), dedent(error))

    def test_path_str_path(self) -> None:
        self.cli.parse("pyproject.toml --strpath tests")
        self.assertIsInstance(self.cli.strpath, str)
        self.assertEqual(self.cli.strpath, "tests")

    def test_path_invalid_type(self) -> None:
        error = "cli: error: argument --boolpath: expected 'str' or 'Path' value. Found 'bool'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("pyproject.toml --boolpath")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout, line_no=3), dedent(error))

    def test_path_invalid_validator(self) -> None:
        with self.assertRaisesRegex(
            ValidatorInitError, "PathValidator - only one of is_dir, is_file, exists can be True at most"
        ):

            class CLI(ArgumentClass):
                path: Path = argfield(validator=PathValidator(is_dir=True, is_file=True))

            CLI()


class TestPathExecuteDecorator(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            infile: Annotated[Path, Args(mode="r")] = argfield()
            outfile: Annotated[Optional[Path], Args(mode="w")] = argfield(
                default="-", validator=PathValidator(is_file=True)
            )

        self.cli = CLI(config=config)

        with open("/tmp/tmp.1.out", "w") as fp:
            fp.write("this is a tmp file")

    def test_path_decorator_open_automatic(self) -> None:
        self.cli.parse("/tmp/tmp.1.out")
        stdout = StringIO()

        @self.cli.execute
        def run(infile: TextIOWrapper, outfile: TextIO) -> None:
            lines = infile.readlines()
            with redirect_stdout(stdout):
                sys.stdout.writelines(lines)
            infile.close()
            self.assertEqual(stdout.getvalue(), "this is a tmp file")
            # do not close outfile which is stdout

    def test_path_decorator_not_open_automatic(self) -> None:
        self.cli.parse("/tmp/tmp.1.out")
        stdout = StringIO()

        @self.cli.execute(open_files=False)
        def run_wo_open(infile: Path, outfile: Path) -> None:
            infile_handle = infile.open()
            line = infile_handle.readlines()
            with redirect_stdout(stdout):
                sys.stdout.writelines(line)
            infile_handle.close()
            self.assertEqual(stdout.getvalue(), "this is a tmp file")
            # do not close outfile which is stdout

    def test_path_decorator_open_directory(self) -> None:
        stdout = StringIO()
        self.cli.parse(".")
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):

            @self.cli.execute
            def run(infile: Path, outfile: Path) -> None:
                pass

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), "cli: error: .: Is a directory [Errno 21]")

    def test_path_decorator_no_such_file(self) -> None:
        stdout = StringIO()
        self.cli.parse("test123")
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):

            @self.cli.execute
            def run(infile: Path, outfile: Path) -> None:
                pass

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), "cli: error: test123: No such file or directory [Errno 2]")


class TestUrlType(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            opt1: Annotated[
                Optional[UrlType], Args(allowed_schemes=["http", "https"], host_required=True, port_required=True)
            ] = argfield("--opt1", "-o")
            opt2: Optional[UrlType] = argfield("--opt2")

        self.cli = CLI(config=config)

    def test_url_args(self) -> None:
        self.cli.parse("--opt1 https://ajatkj.github.com:4553")

        self.assertIsInstance(self.cli.opt1, UrlType)
        if self.cli.opt1:
            self.assertEqual(self.cli.opt1.url.geturl(), "https://ajatkj.github.com:4553")
        self.assertEqual(repr(self.cli.opt1), "https://ajatkj.github.com:4553")

    def test_url_invalid_scheme(self) -> None:
        error = "cli: error: argument -o/--opt1: invalid url [http|https] value: 'ftp://vim.org'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 ftp://vim.org")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_url_missing_host(self) -> None:
        error = "cli: error: argument -o/--opt1: invalid url [http|https] value: 'https://:2455'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 https://:2455")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_url_missing_port(self) -> None:
        error = "cli: error: argument -o/--opt1: invalid url [http|https] value: 'https://localhost'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 https://localhost")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))


class TestUrlValidator(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(
                validator=UrlValidator(allowed_schemes=["http", "https"], host_required=True, port_required=True)
            )
            opt2: Optional[int] = argfield(
                validator=UrlValidator(allowed_schemes=["http", "https"], host_required=True, port_required=True)
            )

        self.cli = CLI(config=config)

    def test_url_args(self) -> None:
        self.cli.parse("--opt1 https://ajatkj.github.com:4553")

        self.assertIsInstance(self.cli.opt1, str)
        self.assertEqual(self.cli.opt1, "https://ajatkj.github.com:4553")

    def test_url_invalid_scheme(self) -> None:
        error = "cli: error: argument --opt1: invalid scheme ftp, expected values ['http', 'https']"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 ftp://vim.org")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_url_missing_host(self) -> None:
        error = "cli: error: argument --opt1: hostname must be present"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 https://:2455")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_url_missing_port(self) -> None:
        error = "cli: error: argument --opt1: port must be present"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 https://localhost")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_url_invalid_type(self) -> None:
        error = "cli: error: argument --opt2: expected 'str' value, found 'int'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt2 10")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))


class TestRegexValidator(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(validator=RegexValidator(r"[a-zA-Z]+"))
            opt2: Optional[int] = argfield(validator=RegexValidator(r"[a-zA-Z]+"))

        self.cli = CLI(config=config)

    def test_regex_args(self) -> None:
        self.cli.parse("--opt1 fooBar")

        self.assertIsInstance(self.cli.opt1, str)
        self.assertEqual(self.cli.opt1, "fooBar")

    def test_regex_invalid_pattern(self) -> None:
        error = "cli: error: argument --opt1: 'foo123' does not match expression '[a-zA-Z]+'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 foo123")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_regex_invalid_type(self) -> None:
        error = "cli: error: argument --opt2: expected 'str' value, found 'int'"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt2 10")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))


class TestConfirmationValidator(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            yes: Optional[bool] = argfield(validator=ConfirmationValidator(answers=["ya", "Yeah!"], ignore_case=False))

        self.cli = CLI(config=config)

    def test_confirmation_yes(self) -> None:
        data = "Yeah!"
        stdout = StringIO()

        with patch("sys.stdin", StringIO(data)), redirect_stdout(stdout):
            self.cli.parse("--yes")

    def test_confirmation_no(self) -> None:
        error = "cli: error: argument --yes: aborted!"
        data = "no"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, patch("sys.stdin", StringIO(data)), redirect_stderr(stdout):
            self.cli.parse("--yes")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_confirmation_with_decorator(self) -> None:
        data = "Yeah!"
        stdout = StringIO()
        with patch("sys.stdin", StringIO(data), redirect_stdout(stdout)):
            self.cli.parse("--yes")

        with redirect_stdout(stdout):

            @self.cli.execute("yes")
            def drop_db(yes: bool) -> None:
                print("Dropping db")

        self.assertEqual(stdout.getvalue(), "Dropping db\n")


class TestLengthValidator(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(validator=LengthValidator(min=5, max=10))
            opt2: Optional[str] = argfield(validator=LengthValidator(min=5))
            opt3: Optional[str] = argfield(validator=LengthValidator(max=10))

        self.cli = CLI(config=config)

    def test_length_validator_args(self) -> None:
        self.cli.parse("--opt1 foobar --opt2 foobar --opt3 bar")
        self.assertIsInstance(self.cli.opt1, str)
        self.assertIsInstance(self.cli.opt2, str)
        self.assertIsInstance(self.cli.opt3, str)
        self.assertEqual(self.cli.opt1, "foobar")
        self.assertEqual(self.cli.opt2, "foobar")
        self.assertEqual(self.cli.opt3, "bar")

    def test_length_not_in_between(self) -> None:
        error = "cli: error: argument --opt1: string length should be between 5 and 10"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt1 foo")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_length_greater_than(self) -> None:
        error = "cli: error: argument --opt2: string length should be greater than 5"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt2 foo")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_length_less_than(self) -> None:
        error = "cli: error: argument --opt3: string length should be less than 10"
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stdout):
            self.cli.parse("--opt3 alongstring")
        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stdout), dedent(error))

    def test_lenght_validator_init_1(self) -> None:
        with self.assertRaisesRegex(ValidatorInitError, "invalid range provided"):

            class CLI(ArgumentClass):
                opt1: str = argfield(validator=LengthValidator())

    def test_lenght_validator_init_2(self) -> None:
        with self.assertRaisesRegex(ValidatorInitError, "invalid range provided"):

            class CLI(ArgumentClass):
                opt1: str = argfield(validator=LengthValidator(min=10, max=5))


class TestFieldValidations(TestCase):
    def test_invalid_field_name(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'_CLI__opt1' cannot have '__' in their name"):

            class CLI(ArgumentClass):
                __opt1: str = argfield()  # This will raise error
                __opt2__: str = argfield()  # This will be completely ignored

            CLI()

    def test_conflicting_longopts(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - conflict in generating 'longopt'. '--opt1' already in use"):

            class CLI(ArgumentClass):
                hello: str = argfield("--opt1")
                opt1: Optional[str] = argfield()

            CLI()

    def test_nargs_1(self) -> None:
        with self.assertRaisesRegex(
            ArgumentError, "'opt1' - 'nargs' must be an integer value \(greater than 2\) for tuple fields"
        ):

            class CLI(ArgumentClass):
                opt1: Optional[Tuple[int, int]] = argfield(nargs="+")

            CLI()

    def test_nargs_2(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'nargs' \(3\) must be same as no. of fields in tuple \(2\)"):

            class CLI(ArgumentClass):
                opt1: Optional[Tuple[int, int]] = argfield(nargs=3)

            CLI()

    def test_nargs_3(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'nargs' must be '\?' or 'None' for union with bool fields"):

            class CLI(ArgumentClass):
                opt1: Optional[Union[bool, int]] = argfield(nargs=3)

            CLI()

    def test_nargs_4(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'nargs' must be '\?' or 'None' to supply 'const'"):

            class CLI(ArgumentClass):
                opt1: Optional[int] = argfield(const=10, nargs=2)

            CLI()

    def test_nargs_5(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - must be list or tuple type when 'nargs' is specified"):

            class CLI(ArgumentClass):
                opt1: Optional[int] = argfield(nargs=2)

            CLI()

    def test_metavar_1(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'metavar' property cannot be suppressed"):

            class CLI(ArgumentClass):
                opt1: Optional[int] = argfield(metavar=SUPPRESS)

            CLI()

    def test_metavar_2(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'cmd' - 'metavar' property not applicable for subcommands"):

            class Command(ArgumentClass):
                opt0: str = argfield()

            class CLI(ArgumentClass):
                cmd: Command = argfield(metavar="cmd")

            CLI()

    def test_aliases(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'cmd' - conflicting command alias 'cmd'"):

            class Command(ArgumentClass):
                opt0: str = argfield()

            class CLI(ArgumentClass):
                cmd: Command = argfield(aliases=["cmd", "cmd"])

            CLI()

    def test_const_1(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'const' property is not allowed for 'bool' type"):

            class CLI(ArgumentClass):
                opt1: Optional[bool] = argfield(const=True)

            CLI()

    def test_const_2(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'const' must be of same type as field"):

            class CLI(ArgumentClass):
                opt1: Optional[str] = argfield(const=10)

            CLI()

    def test_const_3(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'const' property is not allowed for 'positional' arguments"):

            class CLI(ArgumentClass):
                opt1: str = argfield(const=10)

            CLI()

    def test_const_4(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[List[Union[int, bool]]] = argfield(const=10)

        cli = CLI()
        cli.parse("--opt1")
        self.assertEqual(cli.opt1, [10])


class TestFieldDefaults(TestCase):
    def test_default_1(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'default' is invalid for 'required' fields"):

            class CLI(ArgumentClass):
                opt1: str = argfield(default="foo")

            CLI()

    def test_default_union_1(self) -> None:
        with self.assertRaisesRegex(
            ArgumentError, "'opt1' - 'default' must be a valid type from the given union \(int\|float\)"
        ):

            class CLI(ArgumentClass):
                opt1: Optional[Union[int, float]] = argfield(default="foo")

            CLI()

    def test_default_union_2(self) -> None:
        with self.assertRaisesRegex(
            ArgumentError, "'opt1' - 'default' must be a valid type from the given union \(int\|bool\)"
        ):

            class CLI(ArgumentClass):
                opt1: Optional[Union[int, bool]] = argfield(default="False")

            CLI()

    def test_default_tuple_1(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'default' must be a valid tuple \(int,float\)"):

            class CLI(ArgumentClass):
                opt1: Optional[Tuple[int, float]] = argfield(default=("foo", "bar"), nargs=2)

            CLI()

    def test_default_tuple_2(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'default' must be a valid tuple \(int,bool\)"):

            class CLI(ArgumentClass):
                opt1: Optional[List[Tuple[int, bool]]] = argfield(default=[("foo", "False")], nargs=2)

            CLI()

    def test_default_dict_1(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - 'default' must be a valid dict \[int, float\]"):

            class CLI(ArgumentClass):
                opt1: Optional[Dict[int, float]] = argfield(default={10: "foo"})

            CLI()

    def test_default_custom_arg(self) -> None:
        with self.assertRaisesRegex(
            ArgumentError, "'opt1' - 'default' must be of same type as defined by 'type' property, 'bool' given"
        ):

            class CLI(ArgumentClass):
                opt1: Optional[Path] = argfield(default=False)

            CLI()

    def test_default(self) -> None:
        with self.assertRaisesRegex(
            ArgumentError, "'opt1' - 'default' must be of same type as defined by 'type' property, 'str' given"
        ):

            class CLI(ArgumentClass):
                opt1: Optional[int] = argfield(default="foo")

            CLI()


class TestFieldCounter(TestCase):
    def test_counter_type(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - field type must be 'int' or 'float' for counter fields"):

            class CLI(ArgumentClass):
                opt1: Optional[Path] = argfield(counter=True)

            CLI()

    def test_counter_default(self) -> None:
        with self.assertRaisesRegex(ArgumentError, "'opt1' - field type must be 'int' or 'float' for counter fields"):

            class CLI(ArgumentClass):
                opt1: Optional[List[int]] = argfield(counter=True)

            CLI()


class TestArgumentClassRepr(TestCase):
    def test_argument_class_repr(self) -> None:
        class CLI(ArgumentClass):
            opt1: str = argfield()

        cli = CLI()
        self.maxDiff = None
        self.assertEqual(
            repr(cli),
            "UnparsedCLI(opt1=ArgumentField(default=None, dest=opt1, metavar=<opt1>, counter=False, aliases=[], validator=None, help=[str], nargs=None, const=None))",
        )

    def test_argument_class_repr_1(self) -> None:
        class Command(ArgumentClass):
            pass

        class CLI(ArgumentClass):
            command: Command = argfield()

        cli = CLI()
        self.assertEqual(
            repr(cli),
            "UnparsedCLI(command=UnparsedCommand())",
        )


class TestFieldStrAndRepr(TestCase):
    def setUp(self) -> None:
        class CLI(ArgumentClass):
            opt1: str = argfield()

        self.cli = CLI(config=config)

    def test_field_str(self) -> None:
        str_ = str(self.cli.opt1)
        self.maxDiff = None
        self.assertEqual(
            str_,
            "ArgumentField(default=None, dest=opt1, metavar=<OPT1>, counter=False, aliases=[], validator=None, help=[str], nargs=None, const=None)",
        )

    def test_field_repr(self) -> None:
        repr_ = repr(self.cli.opt1)
        self.maxDiff = None
        self.assertEqual(
            repr_,
            "ArgumentField(default=None, dest=opt1, metavar=<OPT1>, counter=False, aliases=[], validator=None, help=[str], nargs=None, const=None)",
        )


class TestCompactUsage(TestCase):
    def test_compact_usage_1(self) -> None:
        usage = """\
        usage: cli [option] <opt1> <opt2> <opt2> [<opt3> ...] <opt4> [<opt4> ...] [<opt5>] command

        positional:
        <opt1>              [str]
        <opt2>              [str]
        <opt3>              [str]
        <opt4>              [str]
        <opt5>              [(int|bool)]

        options:
            --opt6 <value>  [str]

        commands:
        mv

        miscellaneous:
            --help          show this help message and exit
            --version       show version and exit
        """

        class MoveCommand(ArgumentClass):
            source: Path = argfield()

        class CLI(ArgumentClass):
            __version__ = "1.0"
            opt1: str = argfield()
            opt2: List[str] = argfield(nargs=2)
            opt3: List[str] = argfield(nargs="*")
            opt4: List[str] = argfield(nargs="+")
            opt5: Union[int, bool] = argfield(nargs="?")
            mv: MoveCommand = argfield()
            opt6: Optional[str] = argfield()

        cli = CLI(config=ArgumentConfig(compact_usage=True))
        self.maxDiff = None
        stdout = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stdout(stdout):
            cli.parse("--help")
        self.assertEqual(return_code.exception.code, 0)
        self.assertMultiLineEqual(stdout.getvalue(), dedent(usage))


class TestExecuteDecorator(TestCase):
    def test_execute_before_parse(self) -> None:
        class CLI(ArgumentClass):
            opt1: str = argfield()

        cli = CLI()

        with self.assertRaisesRegex(RuntimeError, "arguments need to be parsed before running"):

            @cli.execute
            def excute_opt1(opt1: str) -> None:
                print("opt1 executed")

    def test_execute_unknown_func_args(self) -> None:
        class CLI(ArgumentClass):
            opt1: str = argfield()

        cli = CLI()
        cli.parse("foo")

        with self.assertRaisesRegex(TypeError, "unknown function argument 'opt2'"):

            @cli.execute
            def excute_opt1(opt1: str, opt2: str) -> None:
                print("opt1 executed")

    def test_execute_no_run(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield()

        cli = CLI()
        cli.parse(" ")

        @cli.execute
        def excute_opt1(opt1: str) -> None:
            print("opt1 executed")

    def test_execute_default_func_args(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield()
            opt2: Optional[str] = argfield()

        cli = CLI()
        cli.parse("--opt1 foo")
        stdout = StringIO()
        with redirect_stdout(stdout):

            @cli.execute
            def excute_opt1(opt1: str, opt2: str = "bar") -> None:
                print(f"{opt1}={opt2}")

        self.assertEqual(stdout.getvalue(), "foo=None\n")

    def test_execute_subcommand_args(self) -> None:
        class Command1(ArgumentClass):
            opt2: str = argfield()

        class CLI(ArgumentClass):
            opt1: str = argfield()
            command1: Command1 = argfield()

        cli = CLI()
        cli.parse("foo")

        with self.assertRaisesRegex(TypeError, "invalid function argument 'command1', subcommands are not allowed"):

            @cli.execute
            def excute_opt1(command1: Command1) -> None:
                print("opt1 executed")

    def test_execute_from_subcommand(self) -> None:
        class Command1(ArgumentClass):
            opt1: Optional[str] = argfield()

        class CLI(ArgumentClass):
            command1: Command1 = argfield()

        cli = CLI()
        cli.parse("command1 --opt1 foo")
        stdout = StringIO()
        with redirect_stdout(stdout):

            @cli.command1.execute
            def excute_opt1(opt1: str) -> None:
                print("opt1 executed using subcommand")

        self.assertEqual(stdout.getvalue(), "opt1 executed using subcommand\n")

    def test_execute_main(self) -> None:
        class Subcommand(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command(ArgumentClass):
            sub: Subcommand = argfield()

        class CLI(ArgumentClass):
            cmd: Command = argfield()

        cli = CLI()
        stdout = StringIO()
        cli.parse(" ")
        with redirect_stdout(stdout):

            @cli.execute
            def execute_default_for_script() -> None:
                print("default for script executed")

            @cli.cmd.execute
            def execute_default_for_command() -> None:
                print("default for command executed")

            @cli.cmd.sub.execute
            def execute_default_for_subcommand() -> None:
                print("default for sub-command executed")

            @cli.cmd.sub.execute
            def execute_opt_for_subcommand(opt1: str) -> None:
                print("opt1 for sub-command executed")

            self.assertEqual(stdout.getvalue(), "default for script executed\n")

    def test_execute_main_opt(self) -> None:
        class Subcommand(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command(ArgumentClass):
            sub: Subcommand = argfield()

        class CLI(ArgumentClass):
            cmd: Command = argfield()
            opt2: Optional[str] = argfield()

        cli = CLI()
        stdout = StringIO()
        cli.parse("--opt2 foo")
        with redirect_stdout(stdout):

            @cli.execute
            def execute_default_for_script() -> None:
                print("default for script executed")

            @cli.execute
            def execute_opt_for_script(opt2: str) -> None:
                print("opt for script executed")

            @cli.cmd.execute
            def execute_default_for_command() -> None:
                print("default for command executed")

            @cli.cmd.sub.execute
            def execute_default_for_subcommand() -> None:
                print("default for sub-command executed")

            @cli.cmd.sub.execute
            def execute_opt_for_subcommand(opt1: str) -> None:
                print("opt1 for sub-command executed")

            self.assertEqual(stdout.getvalue(), "opt for script executed\n")

    def test_execute_command(self) -> None:
        class Subcommand(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command(ArgumentClass):
            sub: Subcommand = argfield()

        class CLI(ArgumentClass):
            cmd: Command = argfield()

        cli = CLI()
        stdout = StringIO()
        cli.parse("cmd")
        with redirect_stdout(stdout):

            @cli.cmd.execute
            def execute_default_for_command() -> None:
                print("default for command executed")

            @cli.cmd.sub.execute
            def execute_default_for_subcommand() -> None:
                print("default for sub-command executed")

            @cli.cmd.sub.execute
            def execute_opt_for_subcommand(opt1: str) -> None:
                print("opt1 for sub-command executed")

        self.assertEqual(stdout.getvalue(), "default for command executed\n")

    def test_execute_sub_command(self) -> None:
        class Subcommand(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command(ArgumentClass):
            sub: Subcommand = argfield()

        class CLI(ArgumentClass):
            cmd: Command = argfield()

        cli = CLI()
        stdout = StringIO()
        cli.parse("cmd sub")
        with redirect_stdout(stdout):

            @cli.cmd.execute
            def execute_default_for_command() -> None:
                print("default for command executed")

            @cli.cmd.sub.execute
            def execute_default_for_subcommand() -> None:
                print("default for sub-command executed")

            @cli.cmd.sub.execute
            def execute_opt_for_subcommand(opt1: str) -> None:
                print("opt1 for sub-command executed")

        self.assertEqual(stdout.getvalue(), "default for sub-command executed\n")

    def test_execute_sub_command_opt(self) -> None:
        class Subcommand(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command(ArgumentClass):
            sub: Subcommand = argfield()

        class CLI(ArgumentClass):
            cmd: Command = argfield()

        cli = CLI()
        stdout = StringIO()
        cli.parse("cmd sub --opt 10")
        with redirect_stdout(stdout):

            @cli.cmd.execute
            def execute_default_for_command() -> None:
                print("default for command executed")

            @cli.cmd.sub.execute
            def execute_default_for_subcommand() -> None:
                print("default for sub-command executed")

            @cli.cmd.sub.execute
            def execute_opt_for_subcommand(opt1: str) -> None:
                print("opt1 for sub-command executed")

        self.assertEqual(stdout.getvalue(), "opt1 for sub-command executed\n")


class TestMultiCommand(TestCase):
    def test_multi_command_invalid(self) -> None:
        class Command1(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command2(ArgumentClass):
            opt1: Optional[str] = argfield()

        class CLI(ArgumentClass):
            command1: Command1 = argfield()
            command2: Command2 = argfield()

        with self.assertRaisesRegex(ArgumentError, "'--opt1' is duplicated in subcommand command1, command2"):
            CLI(config=ArgumentConfig(allow_multiple_commands=True))

    def test_multi_command_extra(self) -> None:
        class Command1(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command2(ArgumentClass):
            opt2: Optional[str] = argfield()

        class CLI(ArgumentClass):
            command1: Command1 = argfield()
            command2: Command2 = argfield()

        cli = CLI(config=ArgumentConfig(allow_multiple_commands=True))
        stderr = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stderr):
            cli.parse("command1 --opt1 foo baz command2 --opt2 bar")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stderr), "cli: error: unrecognized arguments baz command2 --opt2 bar")

    def test_multi_command(self) -> None:
        class Command1(ArgumentClass):
            opt1: Optional[str] = argfield()

        class Command2(ArgumentClass):
            opt2: Optional[str] = argfield()

        class CLI(ArgumentClass):
            command1: Command1 = argfield()
            command2: Command2 = argfield()

        cli = CLI(config=ArgumentConfig(allow_multiple_commands=True))
        cli.parse("command1 --opt1 foo command2 --opt2 bar")

        self.assertEqual(cli.command1.opt1, "foo")
        self.assertEqual(cli.command2.opt2, "bar")


class TestExtraArgs(TestCase):
    def test_extra_error(self) -> None:
        class CLI(ArgumentClass):
            opt1: str = argfield()

        cli = CLI(config=ArgumentConfig(extra_arguments="error"))
        stderr = StringIO()
        with self.assertRaises(SystemExit) as return_code, redirect_stderr(stderr):
            cli.parse("foo bar")

        self.assertEqual(return_code.exception.code, 2)
        self.assertEqual(get_err_msg(stderr), "cli: error: unrecognized arguments bar")

    def test_extra_allow(self) -> None:
        class CLI(ArgumentClass):
            opt1: str = argfield()

        cli = CLI(config=ArgumentConfig(extra_arguments="allow"))
        cli.parse("foo bar")

        self.assertEqual(cli.opt1, "foo")
        self.assertEqual(cli.extra_args, ["bar"])

    def test_extra_ignore(self) -> None:
        class CLI(ArgumentClass):
            opt1: str = argfield()

        cli = CLI(config=ArgumentConfig(extra_arguments="ignore"))
        cli.parse("foo bar")

        self.assertEqual(cli.opt1, "foo")
        self.assertEqual(cli.extra_args, None)


class TestInvalidField(TestCase):
    def test_invalid_field(self) -> None:
        class CLI(ArgumentClass):
            opt1: str

        with self.assertRaisesRegex(ArgumentError, "field is not initialized or of invalid type"):
            CLI()


class TestDestFields(TestCase):
    def test_dest_fields_dest_property(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(const="foo")
            _opt2: Optional[str] = argfield(const="bar")

        with self.assertRaisesRegex(ArgumentError, "field starting with _ should have 'dest' property"):
            CLI()

    def test_dest_fields_const_property(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(const="foo")
            _opt2: Optional[str] = argfield(dest="opt1")

        with self.assertRaisesRegex(ArgumentError, "field starting with _ should have 'const' property"):
            CLI()

    def test_dest_fields_invalid_dest(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(const="foo")
            _opt2: Optional[str] = argfield(dest="opt3", const="bar")

        with self.assertRaisesRegex(ArgumentError, "destination field 'opt3' must be a valid argfield"):
            CLI()

    def test_dest_fields_wrong_dest(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(const="foo")
            _opt2: Optional[str] = argfield(dest="opt3", const="bar")

        with self.assertRaisesRegex(ArgumentError, "destination field 'opt3' must be a valid argfield"):
            CLI()

    def test_dest_fields_wrong_dest_type(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[str] = argfield(const="foo")
            _opt2: Optional[str] = argfield(dest="opt1", const="bar")

        with self.assertRaisesRegex(ArgumentError, "destination field 'opt1' must be a list or a tuple"):
            CLI()

    def test_dest_fields_dest_no_const(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[List[str]] = argfield()
            _opt2: Optional[str] = argfield(dest="opt1", const="bar")

        with self.assertRaisesRegex(ArgumentError, "destination field 'opt1' must have a 'const' property"):
            CLI()

    def test_dest_fields_dest(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[List[str]] = argfield(const="foo")
            _opt2: Optional[str] = argfield(dest="opt1", const="bar")

        cli = CLI()
        cli.parse("--opt1 --opt2")
        self.assertIsInstance(cli.opt1, list)
        self.assertEqual(cli.opt1, ["foo", "bar"])

    def test_dest_fields_dest_of_types(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[Tuple[Type[int], ...]] = argfield(nargs=2, const=int)
            _opt2: Optional[Type[str]] = argfield(dest="opt1", const=str)

        cli = CLI()
        cli.parse("--opt1 --opt2")
        self.assertIsInstance(cli.opt1, tuple)
        self.assertEqual(cli.opt1, (int, str))


class TestMisc(TestCase):
    def test_any(self) -> None:
        class CLI(ArgumentClass):
            opt1: Any = argfield()

        cli = CLI()

        cli.parse("10")

        self.assertIsInstance(cli.opt1, str)

    def test_type(self) -> None:
        class CLI(ArgumentClass):
            opt1: Optional[Type[str]] = argfield(const=float)

        cli = CLI()

        cli.parse("--opt1 abc")
        print("----->", cli.opt1)

        self.assertIsInstance(cli.opt1, type)


def get_err_msg(stdout: StringIO, line_no: int = 1) -> str:
    return stdout.getvalue().splitlines()[line_no]


# TODO: Tests
# 1. All validations
# 2. All configs
def start_test() -> None:
    main()


if __name__ == "__main__":
    start_test()
