from typing import List, Optional
from pathlib import Path

from typing_extensions import Annotated, Doc

from typed_argparser import SUPPRESS, ArgumentClass
from typed_argparser.fields import argfield
from typed_argparser.groups import ArgumentGroup


from .common import CommonParameters


class AddCommand(CommonParameters, ArgumentClass):
    __description__ = """\
        This command updates the index using the current content found in the working tree,
        to prepare the content staged for the next commit. It typically adds the current content
        of existing paths as a whole, but with some options it can also be used to add content
        with only part of the changes made to the working tree files applied, or remove paths that
        do not exist in the working tree anymore.

        The "index" holds a snapshot of the content of the working tree, and it is this snapshot that
        is taken  as the contents of the next commit. Thus after making any changes to the working
        tree, and before running the commit command, you must use the add command to add any new or
        modified files to the index.

        This command can be performed multiple times before a commit. It only adds the content of the
        specified file(s) at the time the add command is run; if you want subsequent changes included
        in the next commit, then you must run git add again to add the new content to the index.

        The git status command can be used to obtain a summary of which files have changes that are
        staged for the next commit.

        The git add command will not add ignored files by default. If any ignored files were explicitly
        specified on the command line, git add will fail with a list of ignored files. Ignored files
        reached by directory recursion or filename globbing performed by Git (quote your globs before
        the shell) will be silently ignored. The git add command can be used to add ignored files with
        the -f (force) option.

        Please see git-commit(1) for alternative ways to add content to a commit.
    """
    pass


class MoveCommand(ArgumentClass):
    """
    Move or rename a file, directory, or symlink.

        \tgit mv [-v] [-f] [-n] [-k] <source> <destination>
        \tgit mv [-v] [-f] [-n] [-k] <source> ... <destination directory>

    In the first form, it renames <source>, which must exist and be either a file, symlink or directory, to <destination>.
    In the second form, the last argument has to be an existing directory; the given sources will be moved into this directory.

    The index is updated after successful completion, but the change must still be committed.
    """

    source: Annotated[List[Path], Doc("Source path")] = argfield(nargs="+", help=SUPPRESS)
    desination: Annotated[Path, Doc("Destination file or directory")] = argfield(help=SUPPRESS)

    __epilog__ = """
    This is how move command works
    """


class RestoreCommand(ArgumentClass):
    __description__ = """
    Remove command
    """
    source: Annotated[
        Optional[Path],
        Doc(
            """\
            Restore the working tree files with the content from the given tree. It is common to specify the source
            tree by naming a commit, branch or tag associated with it.

            If not specified, the contents are restored from HEAD if --staged is given, otherwise from the index.

            As a special case, you may use "A...B" as a shortcut for the merge base of A and B if there is exactly one merge base.
            You can leave out at most one of A and B, in which case it defaults
            to HEAD.
            """
        ),
    ] = argfield()
    pass


class RemoveCommand(ArgumentClass, CommonParameters):
    __description__ = """\
        This command updates the index using the current content found in the working tree,
        to prepare the content staged for the next commit. It typically adds the current content of existing paths
        as a whole, but with some options it can also be used to add content with only part of the changes made
        to the working tree files applied, or remove paths that do not exist in the working
        tree anymore.

        The "index" holds a snapshot of the content of the working tree, and it is this snapshot that is taken
        as the contents of the next commit. Thus after making any changes to the working tree,
        and before running the commit command, you must use the add command to add any new or modified files to the index.

        This command can be performed multiple times before a commit. It only adds the content of the specified
        file(s) at the time the add command is run; if you want subsequent changes included in
        the next commit, then you must run git add again to add the new content to the index.

        The git status command can be used to obtain a summary of which files have changes that are staged for the next commit.

        The git add command will not add ignored files by default. If any ignored files were explicitly specified on the
        command line, git add will fail with a list of ignored files. Ignored files
        reached by directory recursion or filename globbing performed by Git (quote your globs before the shell) will be
        silently ignored. The git add command can be used to add ignored files with the -f (force) option.

        Please see git-commit(1) for alternative ways to add content to a commit.
    """
    pass


class AddGroup(ArgumentGroup):
    __title__ = "add"
    __hide_title__ = True
    __group_description__ = "work on the current change (see also: git help everyday)"

    add: Annotated[AddCommand, Doc("Add file contents to the index")] = argfield()
    mv: Annotated[MoveCommand, Doc("Move or rename a file, a directory, or a symlink")] = argfield()
    restore: Annotated[RestoreCommand, Doc("Restore working tree files")] = argfield()
    remove: Annotated[RemoveCommand, Doc("Remove files from the working tree and from the index")] = argfield()
