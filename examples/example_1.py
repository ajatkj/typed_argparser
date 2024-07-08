import os
import sys
from typing import Dict, List, Optional, Tuple, Union

cwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{cwd}/../")

from typed_argparser import ArgumentClass, argfield  # noqa: E402


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
