from datetime import date, datetime, time
from _strptime import TimeRE
from functools import partial
from os import fsencode
from pathlib import Path
import re
from typing import Any, Callable, Generic, List, Optional, Sized, TypeVar, Union
from urllib.parse import urlparse

from typed_argparser.types import _DateTimeType, _DateType
from typed_argparser.utils import validate_url

from .exceptions import ValidationError, ValidatorInitError

F = TypeVar("F")


class ArgumentValidator(Generic[F]):
    def __init__(self, func: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.__runtime_args__ = []
        for k in list(self.kwargs.keys()):
            if self.kwargs[k] == "?":
                self.__runtime_args__.append(k)
                self.kwargs.pop(k)

    def __call__(self, value: F, **kwargs: Any) -> Any:
        # value is supplied by argument parser
        # kwargs is supplied by ArgumentClass parser as runtime arguments
        return partial(self.func, *self.args, **self.kwargs)(value, **kwargs)


class LengthValidator(ArgumentValidator[Sized]):
    def validator(self, value: str, min: Optional[int] = None, max: Optional[int] = None) -> None:
        if min and max and (len(value) < min or len(value) > max):
            raise ValidationError(f"string length should be between {min} and {max}", validator=self)
        if min and len(value) < min:
            raise ValidationError(f"string length should be greater than {min}", validator=self)
        if max and len(value) > max:
            raise ValidationError(f"string length should be less than {max}", validator=self)

    def __init__(self, min: Optional[int] = None, max: Optional[int] = None) -> None:
        if (min and max and min >= max) or (min is None and max is None):
            raise ValidatorInitError("invalid range provided", validator=self)

        super().__init__(self.validator, min=min, max=max)


class RangeValidator(ArgumentValidator[Union[int, float]]):
    def validator(
        self, value: Union[int, float], min: Optional[Union[int, float]] = None, max: Optional[Union[int, float]] = None
    ) -> None:
        if min and max and (value < min or value > max):
            raise ValidationError(f"value should be between {min} and {max}", validator=self)
        if min and value < min:
            raise ValidationError(f"value should be greater than {min}", validator=self)
        if max and value > max:
            raise ValidationError(f"value should be less than {max}", validator=self)

    def __init__(self, min: Optional[Union[int, float]] = None, max: Optional[Union[int, float]] = None):
        if (min and max and min >= max) or (min is None and max is None):
            raise ValidatorInitError("invalid range provided", validator=self)

        super().__init__(self.validator, min=min, max=max)


class DateTimeRangeValidator(ArgumentValidator[date]):
    def validator(
        self, value: Union[date, datetime, time], min: Optional[str] = None, max: Optional[str] = None, format: str = "?"
    ) -> None:
        min_date: Any
        max_date: Any
        # No need to check format here again. It is checked by DateTime types,
        # so format will always be valid here.
        if type(value) is date or isinstance(value, _DateType):
            format = "%Y-%m-%d" if format == "?" else format
            min_date = datetime.strptime(min, format).date() if min else None
            max_date = datetime.strptime(max, format).date() if max else None
        elif type(value) is datetime or isinstance(value, _DateTimeType):
            format = "%Y-%m-%dT%H:%M:%S" if format == "?" else format
            min_date = datetime.strptime(min, format) if min else None
            max_date = datetime.strptime(max, format) if max else None
        else:
            format = "%H:%M:%S" if format == "?" else format
            min_date = datetime.strptime(min, format).time() if min else None
            max_date = datetime.strptime(max, format).time() if max else None

        if min_date and max_date and (value < min_date or value > max_date):
            raise ValidationError(f"should be between {min_date} and {max_date}", validator=self)
        if min_date and value < min_date:
            raise ValidationError(f"should be after {min_date}", validator=self)
        if max_date and value > max_date:
            raise ValidationError(f"should be before {max_date}", validator=self)

    def __init__(self, min: Optional[str] = None, max: Optional[str] = None, format: Optional[str] = "?"):
        if format and format != "?":
            try:
                # KeyError raised when a bad format is found; can be specified as
                # \\, in which case it was a stray % but with a space after it
                TimeRE().compile(format)
            except KeyError as err:
                bad_directive = err.args[0]
                if bad_directive == "\\":  # pragma: no cover
                    bad_directive = "%"
                del err
                raise ValidatorInitError(
                    f"'{bad_directive}' is a bad directive in format '{format}'", validator=self
                ) from None
            # IndexError only occurs when the format string is "%"
            except IndexError:
                raise ValidatorInitError(f"stray %% in format '{format}'", validator=self) from None
        if min is None and max is None:
            raise ValidatorInitError("invalid range provided", validator=self)
        if min is not None and not isinstance(min, str):
            raise ValidatorInitError("invalid format provided for min", validator=self)
        if max is not None and not isinstance(max, str):
            raise ValidatorInitError("invalid format provided for max", validator=self)

        super().__init__(self.validator, min=min, max=max, format=format)


class PathValidator(ArgumentValidator[Union[Path, str]]):
    def validator(
        self,
        value: Union[Path, str],
        is_absolute: bool = False,
        is_dir: bool = False,
        is_file: bool = False,
        exists: bool = False,
    ) -> None:
        if not isinstance(value, (str, Path)):
            raise ValidationError(f"expected 'str' or 'Path' value. Found '{type(value).__name__}'")
        if isinstance(value, str):
            value = Path(value)
        # Perform no validation on stdin/stdout files
        if fsencode(value) == b"-":
            return
        if is_absolute:
            if not value.is_absolute():
                raise ValidationError(f"'{value}' is not an absolute path", validator=self)
        if is_dir:
            if not value.is_dir():
                raise ValidationError(f"'{value}' is not a valid directory", validator=self)
        if is_file:
            if not value.is_file():
                raise ValidationError(f"'{value}' is not a valid file", validator=self)
        if exists:
            if not value.exists():
                raise ValidationError(f"'{value}' does not exist", validator=self)

    def __init__(
        self, is_absolute: bool = False, is_dir: bool = False, is_file: bool = False, exists: bool = False
    ) -> None:
        # Ensure only one is True at most
        true_count = sum([is_dir, is_file, exists])
        if true_count > 1:
            raise ValidatorInitError("only one of is_dir, is_file, exists can be True at most", validator=self)

        super().__init__(self.validator, is_absolute=is_absolute, is_dir=is_dir, is_file=is_file, exists=exists)


class UrlValidator(ArgumentValidator[str]):
    def validator(
        self,
        value: str,
        allowed_schemes: List[str] = [],
        host_required: bool = False,
        port_required: bool = False,
    ) -> None:
        if not isinstance(value, str):
            raise ValidationError(f"expected 'str' value, found '{type(value).__name__}'", validator=self)
        url_components = urlparse(value)
        rc = validate_url(
            url_components, allowed_schemes=allowed_schemes, host_required=host_required, port_required=port_required
        )
        if rc != "":
            raise ValidationError(rc, validator=self)

    def __init__(self, allowed_schemes: List[str] = [], host_required: bool = False, port_required: bool = False) -> None:
        super().__init__(
            self.validator, allowed_schemes=allowed_schemes, host_required=host_required, port_required=port_required
        )


class RegexValidator(ArgumentValidator[str]):
    def validator(self, value: str, pattern: str) -> None:
        if not isinstance(value, str):
            raise ValidationError(f"expected 'str' value, found '{type(value).__name__}'", validator=self)

        regex = re.compile(pattern)

        if not regex.fullmatch(value):
            raise ValidationError(f"'{value}' does not match expression '{pattern}'", validator=self)

    def __init__(self, pattern: str) -> None:
        super().__init__(self.validator, pattern=pattern)


class ConfirmationValidator(ArgumentValidator[Any]):
    def __init__(
        self,
        message: str = "Are you sure you want to proceed?",
        abort_message: Optional[str] = "aborted!",
        answers: List[str] = ["y", "yes"],
        ignore_case: bool = True,
    ) -> None:
        super().__init__(
            self.validator, message=message, abort_message=abort_message, answers=answers, ignore_case=ignore_case
        )

    def validator(self, value: str, message: str, abort_message: str, answers: List[str], ignore_case: bool) -> None:
        try:
            answer = str(input(f"{message} [{'/'.join(answers)}]: ")).strip()
        except KeyboardInterrupt:  # pragma: no cover
            raise ValidationError(abort_message, validator=self)
        if (ignore_case and answer.lower() in [ans.lower() for ans in answers]) or (
            not ignore_case and answer in answers
        ):
            pass
        else:
            raise ValidationError(abort_message, validator=self)
