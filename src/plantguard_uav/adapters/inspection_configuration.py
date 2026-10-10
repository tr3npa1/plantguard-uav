"""Read explicit local inspection JSON without supplying operational defaults."""

import json
from math import isfinite
import os
from pathlib import Path
from stat import S_ISREG
from typing import Final, NoReturn

from pydantic import ValidationError

from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.errors import InspectionConfigurationError

MAX_INSPECTION_CONFIGURATION_BYTES: Final = 64 * 1024


def _object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject repeated decoded keys before a dictionary can discard earlier values."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InspectionConfigurationError(reason="duplicate_key") from None
        result[key] = value
    return result


def _reject_nonfinite_constant(_value: str) -> NoReturn:
    """Reject the nonstandard NaN and infinity tokens accepted by Python's decoder."""
    raise InspectionConfigurationError(reason="nonfinite_number") from None


def _parse_finite_float(token: str) -> float:
    """Reject numeric literals that overflow to infinity during JSON decoding."""
    value = float(token)
    if not isfinite(value):
        raise InspectionConfigurationError(reason="nonfinite_number") from None
    return value


def _validate_unicode_strings(value: object) -> None:
    """Reject escaped lone surrogates without recursively walking parsed JSON."""
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            try:
                current.encode("utf-8")
            except UnicodeEncodeError:
                raise InspectionConfigurationError(reason="invalid_encoding") from None
        elif isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)


def parse_inspection_configuration_json(payload: bytes) -> InspectionFlightConfiguration:
    """Validate bounded UTF-8 JSON bytes as an immutable inspection configuration."""
    if not isinstance(payload, bytes):
        raise InspectionConfigurationError(reason="invalid_input") from None
    if len(payload) > MAX_INSPECTION_CONFIGURATION_BYTES:
        raise InspectionConfigurationError(reason="input_too_large") from None
    try:
        document = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise InspectionConfigurationError(reason="invalid_encoding") from None
    try:
        values = json.loads(
            document,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
            parse_float=_parse_finite_float,
        )
    except (ValueError, RecursionError):
        raise InspectionConfigurationError(reason="invalid_json") from None
    if not isinstance(values, dict):
        raise InspectionConfigurationError(reason="invalid_json") from None
    _validate_unicode_strings(values)
    try:
        return InspectionFlightConfiguration.model_validate(values)
    except ValidationError:
        raise InspectionConfigurationError(reason="invalid_configuration") from None


def load_inspection_configuration(path: Path) -> InspectionFlightConfiguration:
    """Read one trusted local regular file, with bounded I/O and no implicit fallback."""
    try:
        if not S_ISREG(path.stat().st_mode):
            raise InspectionConfigurationError(reason="not_regular_file") from None
        with path.open("rb") as stream:
            if not S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise InspectionConfigurationError(reason="not_regular_file") from None
            payload = stream.read(MAX_INSPECTION_CONFIGURATION_BYTES + 1)
    except (OSError, ValueError):
        raise InspectionConfigurationError(reason="file_unavailable") from None
    return parse_inspection_configuration_json(payload)


class FileInspectionConfigurationSource:
    """Adapt one explicit local file to the read-only configuration-source interface."""

    def __init__(self, path: Path) -> None:
        """Store the caller's trusted path without opening or validating the file yet."""
        self._path = path

    def load(self) -> InspectionFlightConfiguration:
        """Read fresh contents through the existing bounded loader on every call."""
        return load_inspection_configuration(self._path)
