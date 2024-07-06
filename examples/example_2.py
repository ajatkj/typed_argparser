from io import TextIOWrapper
import os
import sys
from typing import Dict, List, Optional, Union
from typing_extensions import Annotated
from pathlib import Path


cwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{cwd}/../")

from typed_argparser.types import Args  # noqa: E402
from typed_argparser import ArgumentClass  # noqa: E402
from typed_argparser.fields import argfield  # noqa: E402


class Example2(ArgumentClass):
    """This example shows how to use the `execute` decorator to execute functions based on the arguments provided."""

    # Positional arguments do not generate short or long options
    opt1: Union[int, str] = argfield(help="opt1 is a mandatory argument which can be an integer or a string")
    opt2: List[str] = argfield(help="opt2 is a mandatory argument and can be used multiple times")
    # Use Annotated from typing to provide arguments to types as shown below
    opt3: Annotated[Optional[Path], Args(mode="w")] = argfield(help="this is an output file argument.")
    # Use Dict type to accept multiple key value pairs
    opt4: Optional[Dict[str, int]] = argfield(help="accept key value pairs. can be used multiple times.")


cli = Example2()

cli.parse("--opt3 output.txt 20 abc")


@cli.execute("opt1", "opt2")
def execute_1(opt1: str, opt2: List[str]):
    print("This function is executed when both function arguments are provided.")
    print(f"opt1: {opt1}, opt2: {opt2}")


@cli.execute("opt3")
def execute_2(opt3: TextIOWrapper):
    opt3.write("This is written to the output file.")


@cli.execute("opt4")
def execute_3(opt4: Dict[str, int]):
    print("This will not be executed as opt4 is not provided.")


"""
Output:
This function is executed when all positional arguments are provided
opt1: 20, opt2: ['abc']

> cat output.txt
───────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
       │ File: output.txt
───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   1   │ This is written to the output file
───────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
"""
