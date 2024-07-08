from pathlib import Path

from typing_extensions import Annotated, Doc, List

from typed_argparser.constants import SUPPRESS
from typed_argparser.fields import argfield


class CommonParameters:
    pathspec: Annotated[
        List[Path],
        Doc(
            """\
            Files to add content from. Fileglobs (e.g.  *.c) can be given to add all matching
            files. Also a leading directory name (e.g.  dir to add dir/file1 and dir/file2)
            can be given to update the index to match the current state of the directory as a
            whole (e.g. specifying dir will record not just a file dir/file1 modified in the
            working tree, a file dir/file2 added to the working tree, but also a file dir/file3
            removed from the working tree). Note that older versions of Git used to ignore
            removed files; use --no-all option if you want to add modified or new files but
            ignore removed ones.

            For more details about the <pathspec> syntax, see the pathspec entry in gitglossary(7)."""
        ),
    ] = argfield(nargs="*")


class Directory:
    directory: Path = argfield(default=None, help=SUPPRESS, nargs="?")
