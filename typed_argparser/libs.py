from argparse import Action
from argparse import ArgumentParser as DefaultArgumentParser
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .constants import SUBPARSER_TITLE, GroupTypeEnum
from .formatter import ArgumentFormatter

if TYPE_CHECKING:  # pragma: no cover
    from argparse import Namespace
    from argparse import _ArgumentGroup as DefaultArgumentGroup

    from .config import ArgumentConfig
    from .constants import ArgumentGroupRegistryType
    from .groups import _ArgumentGroup

__all__ = ["BooleanOptionalAction"]


class BooleanOptionalAction(Action):
    def __init__(
        self,
        option_strings: List[str],
        dest: str,
        default: Optional[bool] = None,
        type: Optional[Any] = None,
        choices: Optional[Any] = None,
        required: bool = False,
        help: Optional[str] = None,
        metavar: Optional[str] = None,
    ) -> None:
        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)
            if option_string.startswith("--"):
                option_string = "--[no-]" + option_string[2:]
                _option_strings.append(option_string)

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=0,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(
        self, parser: "DefaultArgumentParser", namespace: "Namespace", values: Any, option_string: Optional[str] = None
    ) -> None:
        if option_string and option_string in self.option_strings:
            setattr(namespace, self.dest, not option_string.startswith("--no-"))

    def format_usage(self) -> str:
        return " | ".join(self.option_strings)


class ArgumentParser(DefaultArgumentParser):
    # Override certain methods of argparse.ArgumentParser with some sensible defaults
    def __init__(
        self,
        prog: Optional[str] = None,
        description: Optional[str] = None,
        epilog: Optional[str] = None,
    ) -> None:
        super().__init__(
            prog=prog,
            usage=None,
            description=description,
            epilog=epilog,
            parents=[],
            formatter_class=ArgumentFormatter,
            prefix_chars="-",
            fromfile_prefix_chars=None,
            argument_default=None,
            conflict_handler="error",
            add_help=False,
            allow_abbrev=True,
        )

    def set_custom_argument_groups(self, groups: Dict[str, "ArgumentGroupRegistryType"] = {}) -> None:
        # Add custom groups created in ArgumentClass to ArgumentParser to be used in help formatting
        self.groups = groups

    def set_config(self, config: "ArgumentConfig") -> None:
        # Add config object to ArgumentParser to allow handling some parameters via configuration
        self.config = config

    def set_usage(self, usage: Optional[str] = None) -> None:
        # Add custom usage text prepared in ArgumentClass
        if usage:
            self.usage = usage

    def _remove_default_groups(self) -> None:
        # Remove default groups created by ArgumentParser to avoid conflict with our groups
        self._action_groups.remove(self._optionals)
        self._action_groups.remove(self._positionals)

    def format_help(self) -> str:
        # Override format_help to use custom groups instead of groups created by argparse.ArgumentParser
        formatter = self._get_formatter()

        # Usage
        formatter.add_usage(
            self.usage, self._actions, self._mutually_exclusive_groups, prefix=f"{self.config.default_usage_prefix}"
        )

        # Description
        if self.description and self.config.default_description_heading:
            header = self.config.heading_transform(self.config.default_description_heading)
            header = header if self.description.startswith("\n") else "{}\n".format(header)
            formatter._add_item(lambda text: text, [header])
        formatter.add_text(self.description)

        # Argument groups
        for group_details in self.groups.values():
            group = group_details["group"]
            group_type = group_details["group_type"]
            action_group = self._extract_group_actions(group, group_type)
            if action_group:
                formatter.start_section(self.config.heading_transform(group.title) if not group.hide_title else None)
                formatter.add_text(group.description)
                formatter.add_arguments(action_group._group_actions)
                formatter.end_section()

        # Epilog
        formatter.add_text(self.epilog)

        # Determine help from format above
        return formatter.format_help()

    def _extract_group_actions(
        self, group: "_ArgumentGroup", group_type: GroupTypeEnum
    ) -> Optional["DefaultArgumentGroup"]:
        # This method extracts group information from argparse's action groups based on custom groups created by ArgumentClass
        # This helps in grouping of commands which was not possible in argparse.
        if group_type == GroupTypeEnum.FIELD:
            if self._action_groups:
                return next(filter(lambda item: item.title == group.title if item else False, self._action_groups), None)  # type: ignore[arg-type]
            else:  # pragma: no cover
                return None
        else:
            subparser_action = next(filter(lambda item: item.title == SUBPARSER_TITLE, self._action_groups), None)
            if subparser_action is None:  # pragma: no cover
                return None
            subparser_action_ = deepcopy(subparser_action)
            group_actions: List = list(filter(lambda item: item.group == group.title, subparser_action._group_actions))  # type:ignore
            subparser_action_._group_actions = group_actions
            return subparser_action_
