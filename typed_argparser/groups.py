from typing import TYPE_CHECKING, Dict, Optional, Union

from .exceptions import ArgumentError

if TYPE_CHECKING:  # pragma: no cover
    import argparse


class ArgumentGroup:
    if TYPE_CHECKING:  # pragma: no cover
        __title__: str
        __group_description__: Optional[str]
        __exclusive__: bool
        __hide_title__: bool
        __required__: bool


class _ArgumentGroup:
    # This is internal group class, not to be used directly externally.
    # To create ArgumentGroups inherit ArgumentGroup class.

    # Maintain mapping of all instances of this class and return an
    # existing instance if it exists, else create new one.
    _instances: Dict[str, "_ArgumentGroup"] = {}
    __slots__ = (
        "title",
        "description",
        "hide_title",
        "mutually_exclusive",
        "required",
        "_parser",
    )

    def __init__(
        self,
        title: str,
        *,
        description: Optional[str] = None,
        hide_title: bool = False,
        mutually_exclusive: bool = False,
        required: bool = False,
    ) -> None:
        if required and mutually_exclusive is False:
            raise ArgumentError("'required' flag is only applicable when 'mutually_exclusive' is True")
        self.title = title.lower()
        self.description = description
        self.mutually_exclusive = mutually_exclusive
        self.required = required
        self.hide_title = hide_title
        self._parser: Optional[
            Union[argparse._ArgumentGroup, argparse._MutuallyExclusiveGroup, argparse.ArgumentParser]
        ] = None

    @classmethod
    def get_instance(
        cls,
        title: str,
        *,
        description: Optional[str] = None,
        hide_title: bool = False,
        mutually_exclusive: bool = False,
        required: bool = False,
    ) -> "_ArgumentGroup":
        if title in cls._instances:
            return cls._instances[title]
        else:
            group = cls(
                title,
                description=description,
                hide_title=hide_title,
                mutually_exclusive=mutually_exclusive,
                required=required,
            )
            cls._instances[title] = group
            return group

    def __str__(self) -> str:
        return self.title


def arggroup(
    title: str,
    *,
    description: Optional[str] = None,
    hide_title: bool = False,
    mutually_exclusive: bool = False,
    required: bool = False,
) -> _ArgumentGroup:
    return _ArgumentGroup.get_instance(
        title=title,
        description=description,
        hide_title=hide_title,
        mutually_exclusive=mutually_exclusive,
        required=required,
    )
