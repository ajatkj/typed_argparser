from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover
    from .fields import ArgumentField
    from .validators import ArgumentValidator


class ArgumentError(TypeError):
    def __init__(self, message: str, field: Optional["ArgumentField"] = None) -> None:
        super().__init__(message)
        self.field = field

    def __str__(self) -> str:
        if self.field is not None:
            return f"'{self.field._original_name}' - {self.args[0]}"
        else:
            return f"{self.args[0]}"


class ValidationError(TypeError):
    def __init__(self, message: str, validator: Optional["ArgumentValidator[Any]"] = None) -> None:
        self.validator = validator.__class__.__name__
        self.message = message
        super().__init__(message)


class ValidatorInitError(TypeError):
    def __init__(self, message: str, validator: Optional["ArgumentValidator[Any]"] = None) -> None:
        if validator:
            message = f"{validator.__class__.__name__} - {message}"
        super().__init__(message)
