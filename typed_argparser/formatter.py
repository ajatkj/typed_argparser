import re
from argparse import HelpFormatter, _SubParsersAction
from typing import Any, Dict, Iterable, List, Optional

from .constants import SUPPRESS


class ArgumentFormatter(HelpFormatter):
    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=200, width=110, indent_increment=0)

    def _underline_links(self, text: str) -> str:
        url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

        def underline(match: Any) -> str:
            return f"\033[4m{match.group(0)}\033[0m"

        return re.sub(url_pattern, underline, text)

    def _split_lines(self, text: str, width: int) -> List[str]:
        text = text.split("\f")[0]
        return text.splitlines()

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        text = text.split("\f")[0]
        text = self._underline_links(text)
        term_char = text.rstrip()[-1]
        if ord(term_char) == 0:
            text = text[:-1]
            text = self._whitespace_matcher.sub(" ", text).strip()
            import textwrap

            return "\n" + textwrap.fill(text, width, initial_indent=indent, subsequent_indent=indent)
        else:
            return "".join(line.lstrip(" ").replace("\t", "    ") for line in text.splitlines(keepends=True))

    def _format_actions_usage(self, actions: Any, groups: Any) -> str:
        # This method is overridden to print usage for arguments whose help is SUPPRESSED
        # TODO: We supress usage using a different field
        # find group indices and identify actions in groups
        group_actions = set()
        inserts: Dict[int, str] = {}
        for group in groups:
            try:
                start = actions.index(group._group_actions[0])
            except ValueError:
                continue
            else:
                end = start + len(group._group_actions)
                if actions[start:end] == group._group_actions:
                    for action in group._group_actions:
                        group_actions.add(action)
                    if not group.required:
                        if start in inserts:
                            inserts[start] += " ["
                        else:
                            inserts[start] = "["
                        if end in inserts:
                            inserts[end] += "]"
                        else:
                            inserts[end] = "]"
                    else:
                        if start in inserts:
                            inserts[start] += " ("
                        else:
                            inserts[start] = "("
                        if end in inserts:
                            inserts[end] += ")"
                        else:
                            inserts[end] = ")"
                    for i in range(start + 1, end):
                        inserts[i] = "|"

        # collect all actions format strings
        parts = []
        for i, action in enumerate(actions):
            # produce all arg strings
            if not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                part = self._format_args(action, default)

                # if it's in a group, strip the outer []
                if action in group_actions:
                    if part[0] == "[" and part[-1] == "]":
                        part = part[1:-1]

                # add the action string to the list
                parts.append(part)

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = "%s" % option_string

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = self._format_args(action, default)
                    part = "%s %s" % (option_string, args_string)

                # make it look optional if it's not required or in a group
                if not action.required and action not in group_actions:
                    part = "[%s]" % part

                # add the action string to the list
                parts.append(part)

        # insert things at the necessary indices
        for i in sorted(inserts, reverse=True):
            parts[i:i] = [inserts[i]]

        # join all the action items with spaces
        text = " ".join([item for item in parts if item is not None])

        # clean up separators for mutually exclusive groups
        open = r"[\[(]"
        close = r"[\])]"
        text = re.sub(r"(%s) " % open, r"\1", text)
        text = re.sub(r" (%s)" % close, r"\1", text)
        text = re.sub(r"%s *%s" % (open, close), r"", text)
        text = re.sub(r"\(([^|]*)\)", r"\1", text)
        text = text.strip()

        # return the text
        return text

    def _format_action_invocation(self, action: Any) -> str:
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                shortopt = any(option_string.count("-", 0, 2) == 1 for option_string in action.option_strings)
                parts.extend(action.option_strings)
            # if the Optional takes a value, format is:
            #    -s, --long ARGS or
            #        --long ARGS or
            #    -s ARGS
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                shortopt = any(option_string.count("-", 0, 2) == 1 for option_string in action.option_strings)
                longopt = any(option_string.count("-", 0, 2) == 2 for option_string in action.option_strings)
                for option_string in action.option_strings:
                    if option_string.startswith("--"):
                        parts.append("%s %s" % (option_string, args_string))
                    else:
                        if longopt:
                            parts.append("%s" % (option_string))
                        else:
                            parts.append("%s %s" % (option_string, args_string))

            parts.insert(0, "  ") if shortopt is False else None

            delimiter = ", " if shortopt else "  "
            return delimiter.join(parts)

    def add_usage(
        self, usage: Optional[str], actions: Any, groups: Iterable[Any], prefix: Optional[str] = "USAGE: "
    ) -> None:
        # This method is overridden to change the default prefix
        if usage is not SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    class _Section(object):
        # Overridden format_help method to not use ":" after heading

        def __init__(self, formatter: Any, parent: Any, heading: Optional[str] = None) -> None:
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items: List[Any] = []

        def format_help(self) -> Any:
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ""

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = "%*s%s\n" % (current_indent, "", self.heading)
            else:
                heading = ""

            # join the section-initial newline, the heading and the help
            return join(["\n", heading, item_help, "\n"])

    def _format_action(self, action: Any) -> str:
        # This method has been overridden to skip writing header for subparser (commands)
        # Command group header is printed using custom groups

        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)
        is_subparser = False
        if isinstance(action, _SubParsersAction):
            is_subparser = True
            action.help = None

        # no help; start on same line and add a final newline
        if not action.help:
            tup: Any = self._current_indent, "", action_header
            action_header = "%*s%s\n" % tup

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, "", action_width, action_header
            action_header = "%*s%-*s  " % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, "", action_header
            action_header = "%*s%s\n" % tup
            indent_first = help_position

        # collect the pieces of the action help
        if not is_subparser:
            parts = [action_header]
        else:
            parts = []

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            parts.append("%*s%s\n" % (indent_first, "", help_lines[0].strip()))
            for line in help_lines[1:]:
                parts.append("%*s%s\n" % (help_position, "", line.strip()))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith("\n"):
            parts.append("\n")

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)
