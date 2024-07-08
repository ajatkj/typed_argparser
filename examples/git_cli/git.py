import os
import pathlib
import sys
from typing import Dict, Optional, Union

cwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{cwd}/../../")

from typed_argparser import ArgumentClass, argfield  # noqa: E402
from typed_argparser.constants import SUPPRESS  # noqa: E402
from typed_argparser.config import ArgumentConfig  # noqa: E402
from examples.git_cli.add_group import AddGroup  # noqa: E402
from examples.git_cli.init_group import InitGroup  # noqa: E402
from examples.git_cli.remote_group import RemoteCommand  # noqa: E402


class Git(ArgumentClass, AddGroup, InitGroup):
    """\
    Git is a fast, scalable, distributed revision control system with an unusually
    rich command set that provides both high-level operations and full access to
    internals.

    See gittutorial(7) to get started, then see giteveryday(7) for a useful minimum
    set of commands. The Git User’s Manual[1] has a more in-depth introduction.

    After you mastered the basic concepts, you can come back to this page to learn
    what commands Git offers. You can learn more about individual Git commands with
    "git help command". gitcli(7) manual page gives you an overview of the command-
    line command syntax.

    A formatted and hyperlinked copy of the latest Git documentation can be viewed
    at https://git.github.io/htmldocs/git.html or https://git-scm.com/docs.
    """

    __epilog__ = """
    'git help -a' and 'git help -g' list available subcommands and some concept guides.
    See 'git help <command>' or 'git help <concept>' to read about a specific subcommand
    or concept. See 'git help git' for an overview of the system.
    """

    current_path: Optional[pathlib.Path] = argfield("-C", help=SUPPRESS)
    config: Optional[Dict[str, str]] = argfield("-c", help=SUPPRESS)
    config_env: Optional[str] = argfield(help=SUPPRESS)
    exec_path: Optional[Union[bool, int]] = argfield(help=SUPPRESS)
    remote: RemoteCommand = argfield()


git_cli = Git(
    config=ArgumentConfig(
        compact_usage=False,
        show_default_in_help=False,
        show_type_in_help=False,
        allow_multiple_commands=False,
        groups_sort_order=["positional", "options", "init", "add", "*", "miscellaneous"],
    )
)
git_cli.parse()


@git_cli.execute
def show_help() -> None:
    git_cli.print_help()


@git_cli.remote.execute
def show_remote() -> None:
    git_cli.remote.print_help()


@git_cli.remote.add.execute
def add_remote(name: str, url: str, *, branch: Optional[str] = None) -> None:
    print(f"Adding remote {name} at {url}")
    print("Info:")
    print(f"\tBranch {branch}")
