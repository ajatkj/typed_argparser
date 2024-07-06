from typing import Literal, Optional

from typed_argparser.constants import SUPPRESS
from typed_argparser.fields import argfield
from typed_argparser.groups import ArgumentGroup
from typed_argparser.parser import ArgumentClass
from typed_argparser.validators import UrlValidator


class RemoteAddCommandOptions(ArgumentGroup):
    __title__ = "options1"
    __hide_title__ = True

    fetch: Optional[bool] = argfield("-f", "--fetch", help="fetch the remote branches")
    tags: Optional[bool] = argfield(
        help="import all tags and associated objects when fetching\nor do not fetch any tag at all (--no-tags)"
    )
    track: Optional[str] = argfield("-t", "--track", help="Branch to add", metavar="branch")
    master: Optional[str] = argfield("-m", help="master branch", metavar="master")
    mirror: Optional[Literal["fetch", "push"]] = argfield(help="set up remote as a mirror to push to or fetch from")


class RemoteAddCommand(ArgumentClass, RemoteAddCommandOptions):
    __usage__ = "git remote add [<options>] <name> <url>"

    name: str = argfield(help=SUPPRESS)
    url: str = argfield(validator=UrlValidator(), help=SUPPRESS)


class RemoteCommand(ArgumentClass):
    __description__ = "Manage set of tracker repositories"

    add: RemoteAddCommand = argfield(help="Add a remote named <name> for the repo at <URL>")
