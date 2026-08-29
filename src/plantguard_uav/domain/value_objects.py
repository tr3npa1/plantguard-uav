"""Reusable validation primitives for persisted and transmitted domain contracts."""

from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from typing import Annotated, Any, Final, Literal, Self

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, StringConstraints

type SchemaVersion = Literal["1.0"]
SCHEMA_VERSION: Final[SchemaVersion] = "1.0"

type OpaqueIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1),
]
type NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True, min_length=1),
]


def _reject_numeric_datetime(value: object) -> object:
    """Reject ambiguous Unix numbers while permitting datetime and ISO string inputs."""
    if isinstance(value, (int, float)):
        msg = "Domain timestamps must be datetime objects or ISO 8601 strings."
        raise ValueError(msg)
    return value


def _normalise_utc_datetime(value: datetime) -> datetime:
    """Reject naive times and convert aware values to the canonical UTC timezone."""
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Persisted domain timestamps must include timezone information."
        raise ValueError(msg)
    return value.astimezone(UTC)


type UtcDateTime = Annotated[
    datetime,
    BeforeValidator(_reject_numeric_datetime),
    AfterValidator(_normalise_utc_datetime),
]


class ContractModel(BaseModel):
    """Strict immutable base for domain values that may cross a process boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        validate_default=True,
    )

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        """Return a new contract after validating every original and updated field."""
        values = self.model_dump(round_trip=True)
        if deep:
            values = deepcopy(values)
        if update:
            values.update(deepcopy(dict(update)) if deep else update)
        return type(self).model_validate(values)
