from datetime import date, datetime, time
from _strptime import TimeRE
from os import fsencode
from pathlib import Path
import re
from typing import Any, Generic, List, Optional, Sized, TypeVar, Union
from urllib.parse import urlparse

from typed_argparser.types import _DateTimeType, _DateType
from typed_argparser.utils import validate_url

from .exceptions import ValidationError, ValidatorInitError

F = TypeVar("F")


class ArgumentValidator(Generic[F]):
    def __call__(self, value: F, **kwargs: Any) -> Any:
        # value is supplied by argument parser
        # kwargs is supplied by ArgumentClass parser as runtime arguments
        if hasattr(self, "validator"):
            return self.validator(value, **kwargs)


class LengthValidator(ArgumentValidator[Sized]):
    def validator(self, value: str) -> None:
        if self.min and self.max and (len(value) < self.min or len(value) > self.max):
            raise ValidationError(f"string length should be between {self.min} and {self.max}", validator=self)
        if self.min and len(value) < self.min:
            raise ValidationError(f"string length should be greater than {self.min}", validator=self)
        if self.max and len(value) > self.max:
            raise ValidationError(f"string length should be less than {self.max}", validator=self)

    def __init__(self, min: Optional[int] = None, max: Optional[int] = None) -> None:
        if (min and max and min >= max) or (min is None and max is None):
            raise ValidatorInitError("invalid range provided", validator=self)
        self.min = min
        self.max = max


class RangeValidator(ArgumentValidator[Union[int, float]]):
    def validator(self, value: Union[int, float]) -> None:
        if self.min and self.max and (value < self.min or value > self.max):
            raise ValidationError(f"value should be between {self.min} and {self.max}", validator=self)
        if self.min and value < self.min:
            raise ValidationError(f"value should be greater than {self.min}", validator=self)
        if self.max and value > self.max:
            raise ValidationError(f"value should be less than {self.max}", validator=self)

    def __init__(self, min: Optional[Union[int, float]] = None, max: Optional[Union[int, float]] = None):
        if (min and max and min >= max) or (min is None and max is None):
            raise ValidatorInitError("invalid range provided", validator=self)

        self.min = min
        self.max = max

        # super().__init__(self.validator)


class DateTimeRangeValidator(ArgumentValidator[date]):
    def validator(self, value: Union[date, datetime, time], format: str = "?") -> None:
        min_date: Any
        max_date: Any
        # No need to check format here again. It is checked by DateTime types,
        # so format will always be valid here.
        format = self.format if self.format != "?" else format
        if type(value) is date or isinstance(value, _DateType):
            format = "%Y-%m-%d" if format == "?" else format
            min_date = datetime.strptime(self.min, format).date() if self.min else None
            max_date = datetime.strptime(self.max, format).date() if self.max else None
        elif type(value) is datetime or isinstance(value, _DateTimeType):
            format = "%Y-%m-%dT%H:%M:%S" if format == "?" else format
            min_date = datetime.strptime(self.min, format) if self.min else None
            max_date = datetime.strptime(self.max, format) if self.max else None
        else:
            format = "%H:%M:%S" if format == "?" else format
            min_date = datetime.strptime(self.min, format).time() if self.min else None
            max_date = datetime.strptime(self.max, format).time() if self.max else None

        if min_date and max_date and (value < min_date or value > max_date):
            raise ValidationError(f"should be between {min_date} and {max_date}", validator=self)
        if min_date and value < min_date:
            raise ValidationError(f"should be after {min_date}", validator=self)
        if max_date and value > max_date:
            raise ValidationError(f"should be before {max_date}", validator=self)

    def __init__(self, min: Optional[str] = None, max: Optional[str] = None, format: str = "?"):
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

        self.min = min
        self.max = max
        self.format = format


class PathValidator(ArgumentValidator[Union[Path, str]]):
    def validator(self, value: Union[Path, str]) -> None:
        if not isinstance(value, (str, Path)):
            raise ValidationError(f"expected 'str' or 'Path' value. Found '{type(value).__name__}'")
        if isinstance(value, str):
            value = Path(value)
        # Perform no validation on stdin/stdout files
        if fsencode(value) == b"-":
            return
        if self.is_absolute:
            if not value.is_absolute():
                raise ValidationError(f"'{value}' is not an absolute path", validator=self)
        if self.is_dir:
            if not value.is_dir():
                raise ValidationError(f"'{value}' is not a valid directory", validator=self)
        if self.is_file:
            if not value.is_file():
                raise ValidationError(f"'{value}' is not a valid file", validator=self)
        if self.exists:
            if not value.exists():
                raise ValidationError(f"'{value}' does not exist", validator=self)

    def __init__(
        self, is_absolute: bool = False, is_dir: bool = False, is_file: bool = False, exists: bool = False
    ) -> None:
        # Ensure only one is True at most
        true_count = sum([is_dir, is_file, exists])
        if true_count > 1:
            raise ValidatorInitError("only one of is_dir, is_file, exists can be True at most", validator=self)

        self.is_absolute = is_absolute
        self.is_dir = is_dir
        self.is_file = is_file
        self.exists = exists


class UrlValidator(ArgumentValidator[str]):
    def validator(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValidationError(f"expected 'str' value, found '{type(value).__name__}'", validator=self)
        url_components = urlparse(value)
        rc = validate_url(
            url_components,
            allowed_schemes=self.allowed_schemes,
            host_required=self.host_required,
            port_required=self.port_required,
        )
        if rc != "":
            raise ValidationError(rc, validator=self)

    def __init__(self, allowed_schemes: List[str] = [], host_required: bool = False, port_required: bool = False) -> None:
        self.allowed_schemes = allowed_schemes
        self.host_required = host_required
        self.port_required = port_required


class RegexValidator(ArgumentValidator[str]):
    def validator(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValidationError(f"expected 'str' value, found '{type(value).__name__}'", validator=self)

        regex = re.compile(self.pattern)

        if not regex.fullmatch(value):
            raise ValidationError(f"'{value}' does not match expression '{self.pattern}'", validator=self)

    def __init__(self, pattern: str) -> None:
        self.pattern = pattern


class ConfirmationValidator(ArgumentValidator[Any]):
    def __init__(
        self,
        message: str = "Are you sure you want to proceed?",
        abort_message: str = "aborted!",
        answers: List[str] = ["y", "yes"],
        ignore_case: bool = True,
    ) -> None:
        self.message = message
        self.abort_message = abort_message
        self.answers = answers
        self.ignore_case = ignore_case

    def validator(self, value: str) -> None:
        try:
            answer = str(input(f"{self.message} [{'/'.join(self.answers)}]: ")).strip()
        except KeyboardInterrupt:  # pragma: no cover
            raise ValidationError(self.abort_message, validator=self)
        if (self.ignore_case and answer.lower() in [ans.lower() for ans in self.answers]) or (
            not self.ignore_case and answer in self.answers
        ):
            pass
        else:
            raise ValidationError(self.abort_message, validator=self)
