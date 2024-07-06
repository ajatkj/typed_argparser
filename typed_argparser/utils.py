from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict
from urllib.parse import ParseResult

if TYPE_CHECKING:  # pragma: no cover
    from .constants import ArgumentGroupRegistryType


class AnnotationType(TypedDict):
    origin: Any
    args: Any
    value: Any
    optional: Any


def transform_heading(heading: str) -> str:
    return "{}:".format(heading.lower())


def transform_metavar(metavar: str) -> str:
    return "<{}>".format(metavar.lower())


def qualified_name(name: str, qual: Optional[str] = None) -> str:
    return "{}__{}".format(qual, name) if qual and name else str(name)


def _remove_duplicates(keys: List[str]) -> List[str]:
    # Remove duplicates without chaning the order of the list
    seen = set()
    updated_keys = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            updated_keys.append(key)
    return updated_keys


def sort_groups(
    groups: Dict[str, "ArgumentGroupRegistryType"], sorting_list: List[str]
) -> Dict[str, "ArgumentGroupRegistryType"]:
    if "*" not in sorting_list:
        sorting_list.append("*")
    sorting_list = _remove_duplicates(sorting_list)
    sorting_list = [key.lower() for key in sorting_list]
    groups_keys = [key.lower() for key in groups.keys()]
    wildcard_keys = [key for key in groups_keys if key.lower() not in [k.lower() for k in sorting_list]]
    sorted_keys: List[str] = []
    for key in sorting_list:
        if key not in groups_keys and key != "*":
            continue
        sorted_keys.extend(wildcard_keys) if key == "*" else sorted_keys.append(key)

    sorted_dict = {key: groups[key] for key in sorted_keys}
    return sorted_dict


def validate_url(
    url_components: ParseResult, allowed_schemes: List[str] = [], host_required: bool = False, port_required: bool = False
) -> str:
    scheme = url_components.scheme
    hostname = url_components.hostname
    port = url_components.port

    if url_components.netloc == "":
        return "invalid url structure"

    if allowed_schemes:
        if scheme not in allowed_schemes:
            return f"invalid scheme {scheme}, expected values {allowed_schemes}"

    if host_required:
        if hostname is None:
            return "hostname must be present"

    if port_required:
        if port is None:
            return "port must be present"

    return ""
