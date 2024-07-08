from pathlib import Path
from typing import Optional

from typing_extensions import Annotated, Doc

from typed_argparser import ArgumentClass, argfield
from typed_argparser.groups import ArgumentGroup

from .common import Directory


class InitCommand(ArgumentClass, Directory):
    quiet: Optional[bool] = argfield(
        "-q", help="Only print error and warning messages; all other output will be suppressed."
    )
    branch: Annotated[
        Optional[Path], Doc("Use the specified name for the initial branch in the newly created repository.")
    ] = argfield("--initial-branch", "-b")


class CloneCommand(ArgumentClass, Directory):
    pass


class InitGroup(ArgumentGroup):
    __title__ = "init"
    __hide_title__ = True
    __group_description__ = "start a working area (see also: git help tutorial)"

    init: Annotated[InitCommand, Doc("Create an empty Git repository or reinitialize an existing one")] = argfield()
    clone: Annotated[InitCommand, Doc("Clone a repository into a new directory")] = argfield()
