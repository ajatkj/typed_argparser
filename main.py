import pathlib
from typing import Optional, List, Dict, Union
from typed_argparser import ArgumentClass, ArgumentConfig
from typed_argparser.fields import argfield
from typed_argparser.validators import (
    PathValidator,
)
from typed_argparser.types import Args
from enum import Enum
from typing_extensions import Annotated, Doc


class MyType:
    def __init__(self, value: str) -> None:
        self.value = value.lower() == "true"

    def __call__(self, value: str) -> "MyType":
        return type(self)(value)


class Choices(Enum):
    choice_1 = "CHOICE1"
    choice_2 = "CHOICE2"
    choice_3 = "CHOICE3"


class Foo(ArgumentClass):
    __description__ = "Bar commands"

    baz: int = argfield(help="baz command does this")


class Bar(ArgumentClass):
    __description__ = "Bla commands"

    baz: Optional[int] = argfield()
    jak: Optional[List[Dict[str, str]]] = argfield(nargs=2)


config = ArgumentConfig(
    groups_sort_order=["commands", "*"],
    show_none_default=False,
    compact_usage=False,
    extra_arguments="error",
    allow_multiple_commands=True,
)


# Optional    shortopts/longopts        field type
# Yes         Yes                         Options with required False
# Yes         No                          Invalid
# No          Yes                         Options with required True
# No          No                          positional


def argvalidator(x, y, value):
    if value < x:
        return False
    if value > y:
        return False
    return True


# a = DateType()("2020-10-23")
# print(a, type(a))


class Subcommand1(ArgumentClass):
    opt1: str = argfield()


class Command1(ArgumentClass):
    opt1: Optional[str] = argfield()
    sub: Subcommand1 = argfield()


class Arguments(ArgumentClass):
    """
    This is a test CLI Program
    """

    __epilog__ = "This is epilog"
    __version__ = "1.0"
    __program__ = "main"

    # val: Annotated[int, Args(), Doc("int value")] = argfield(validator=RangeValidator(max=40))
    # val: str = argfield(validator=LengthValidator(4, 30))
    # start_date: Annotated[Optional[time], Args(format="%H:%M", a="12:31")] = argfield(
    #     validator=DateTimeRangeValidator(min="12:30", max="13:30"), default=time(12, 31)
    # )
    # input: Annotated[Optional[PathType], Args(mode="r"), Doc("input path")] = argfield(
    #     validator=PathValidator(is_file=True)
    # )
    # output: Optional[PathType] = argfield()
    output: Annotated[Optional[pathlib.Path], Args(mode="w"), Doc("output path")] = argfield(
        validator=PathValidator(is_file=False), default=pathlib.Path("output.txt")
    )
    # cmd1: Command1 = argfield()
    # anyarg: Any = argfield()
    # unannotated = argfield()
    # defa: Tuple[int, ...] = argfield(nargs=4)
    # dt1: Annotated[Optional[datetime], Args(format="%Y.%m.%dT%H%M%S")] = argfield(
    #     validator=DateTimeRangeValidator(min="2020.01.01T123000", max="2020.02.01T123000")
    # )
    # start_date_0: Annotated[DateType, Doc("start"), Args(format="%d-%m-%Y")] = argfield()
    # start_date: Optional[DateTimeType] = argfield()
    # start_time_1: Annotated[Optional[TimeType], Args(format="%M:%S")] = argfield()
    # start_time: Annotated[Optional[TimeType], Args(format="%H:%S")] = argfield()
    # start_time_0: Optional[TimeType] = argfield()
    # start_time: Optional[TimeType] = argfield()
    # start_date_1: Optional[DateType] = argfield()
    # end_date: Annotated[TimeType, Doc("start"), Args(format="%H:%M")] = argfield()
    # end_time: datetime = argfield()
    # sam: Annotated[str, Doc("Help for sam")] = argfield()
    # pos: Union[int, bool] = argfield(help="This enables option 1 for you")
    # sam: List[Optional[Union[int, bool, str]]] = argfield(nargs=2)
    # url: Annotated[Optional[str], Doc("hello")] = argfield(validator=UrlValidator(allowed_schemes=["https", "ssh"]))
    # pat: Optional[str] = argfield(validator=RegexValidator(pattern=r"^[a-zA-Z0-9]+$"))
    # yes: Optional[bool] = argfield(validator=ConfirmationValidator())
    # jal: Optional[List[Tuple[int, ...]]] = argfield(nargs=3, default=[(10, 10)])
    # pal: Optional[List[int]] = argfield()
    # kai: Optional[Dict[str, List[int]]] = argfield(nargs=2)
    # jak: Optional[List[Dict[str, str]]] = argfield(nargs=2)
    jak: Optional[Union[int, float, bool, str]] = argfield()
    # rnoargs: Annotated[Optional[Union[int, bool]], Doc("This is docstring for noargs")] = argfield()
    # args: Optional[List[Literal["a", "b", "c"]]] = argfield(nargs=2)
    # args1: Optional[List[str]] = argfield(nargs="*")
    # args2: Optional[List[str]] = argfield(nargs=2, shortopts="-r")
    # args3: Optional[Union[bool, str]] = argfield(default=True)
    # args3: Annotated[Optional[union_type], Args(types=[int, bool])] = argfield(default=10.2)
    # args3: Annotated[Optional[Union[int, bool]], Args(types=[int, bool])] = argfield(default=True)
    # args4: Optional[int] = argfield(group=ex_group1)
    # args5: Optional[float] = argfield(group=ex_group1)
    # args6: Optional[float] = argfield(group=ex_group2, help="hello", metavar="args")
    # foo: Annotated[Foo, Doc("This is subcommand 1"), Args(foo="bar")] = argfield(aliases=[])
    # foo: Foo = argfield()
    # bar: Annotated[Bar, Doc("This is subcommand 2")] = argfield(aliases=["aaa", "bbb"])
    # baz: Optional[Dict[str, Union[int, bool]]] = argfield(help="Use int if int present else bool.")

    # string: Annotated[Optional[Tuple[str, Type]], Doc("Add string to the list")] = argfield(const="string")
    # string: Annotated[Optional[List[Any]], Doc("Add string to the list")] = argfield(const="string")
    # _integer: Annotated[Optional[Type], Doc("Add integer to the list")] = argfield(dest="string", const=int)
    # _float: Annotated[Optional[Type], Doc("Add integer to the list")] = argfield(dest="string", const=float)
    # help = argfield(longopts="--help", shortopts="-h", help="this is my help message")
    # my_choices: Choices = argfield()


# a = pathlib.Path("a/b/c/d/e/f")
# print(a)
args = Arguments(config=config)
# print(args.__argclass_fields__)
args.parse()
print(args)
# print(args.url.path)
# print(args.url.url.scheme)
# print(args.input.open())
# print(args.start_date, type(args.start_date))
# a = pathlib.Path()
# args.group_foo
# print(args.Group1.group_foo)
# print(args.bar.baz, type(args.bar.baz))
# print(f"{args.foo}, {type(args.foo)=}")
# print(f"{args.bar}, {type(args.bar)=}")
# print(f"{args.baz}, {type(args.baz)=}")
# print(f"{args._bam}, {type(args._bam)=}")
# print(f"{args.true_or_false}, {type(args.true_or_false)=}")
# print(f"{args.menu}, {type(args.menu)=}")
# print(f"{args.verbose}, {type(args.verbose)=}")

# args = parse_args(b)
# print(args.input, type(args.input))


# @args.cmd1.execute
# def exc_def():
#     print("This is default cmd1")


# @args.cmd1.execute()
# def exc(opt1):
#     print(f"------- {opt1} -------")


# @args.cmd1.execute()
# def exc_1(opt1):
#     print(f"++++++ {opt1} ++++++")


# @args.execute(immediately=False)
# def this_in_fun(val: int, v: int = 10, hello: str = "world", foo1: Optional[str] = None):
#     print(val, v, hello, foo1)


# this_in_fun(foo1="hello")

# @args.run
# def this_is_args(val: int, args: str, input: path):
#     print("running only if args is found")


# @args.run(command="foo")
# def run_foo_baz(baz: int):
#     print("running foo-baz with value, ", baz)


# @args.execute(open_files=True)
def inout(input, output):
    print(type(input), type(output))
    """Copy contents of INPUT to OUTPUT."""
    # while True:
    #     chunk = input.read(1024)
    #     if not chunk:
    #         break
    #     output.write(chunk)


# @args.execute()
def dropdb(yes):
    if yes:
        print("Db dropped")
    else:
        print("not dropped")
