"""JSON parser examples are synthetic test inputs, never approved flight profiles."""

import json
import traceback
from typing import cast

from pydantic import ValidationError
import pytest

from plantguard_uav.adapters.inspection_configuration import (
    MAX_INSPECTION_CONFIGURATION_BYTES,
    parse_inspection_configuration_json,
)
from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.errors import ConfigurationError, InspectionConfigurationError


@pytest.fixture
def synthetic_values() -> dict[str, object]:
    return {
        "configuration_id": "synthetic-parser-test",
        "configuration_version": "synthetic-revision-a",
        "operating_environment": "nominal_dry_daylight",
        "survey": {
            "altitude_agl_m": 12,
            "speed_m_s": 3,
            "front_overlap_fraction": 0.5,
            "side_overlap_fraction": 0.25,
        },
        "revisit": {"altitude_agl_m": 6, "speed_m_s": 4},
    }


@pytest.fixture
def synthetic_json(synthetic_values: dict[str, object]) -> bytes:
    return json.dumps(synthetic_values).encode("utf-8")


def _assert_parser_failure(payload: bytes, reason: str) -> InspectionConfigurationError:
    with pytest.raises(InspectionConfigurationError) as captured:
        parse_inspection_configuration_json(payload)

    error = captured.value
    assert isinstance(error, ConfigurationError)
    assert error.error_code == "configuration_error"
    assert error.public_message == "Inspection configuration could not be loaded."
    assert str(error) == error.public_message
    assert error.context == {"operation": "load_inspection_configuration", "reason": reason}
    return error


def _set_attribute(model: object, name: str, value: object) -> None:
    setattr(model, name, value)


def test_parser_reuses_existing_model_and_default_schema_versions(
    synthetic_values: dict[str, object], synthetic_json: bytes
) -> None:
    configuration = parse_inspection_configuration_json(synthetic_json)

    assert isinstance(configuration, InspectionFlightConfiguration)
    assert configuration == InspectionFlightConfiguration.model_validate(synthetic_values)
    assert configuration.schema_version == "1.0"
    assert configuration.survey.schema_version == "1.0"
    assert configuration.revisit.schema_version == "1.0"
    assert type(configuration.survey.altitude_agl_m) is float
    assert type(configuration.revisit.speed_m_s) is float
    assert (
        parse_inspection_configuration_json(configuration.model_dump_json().encode("utf-8"))
        == configuration
    )


@pytest.mark.parametrize("ensure_ascii", [True, False])
def test_parser_accepts_unicode_and_preserves_domain_identifier_normalization(
    synthetic_values: dict[str, object], ensure_ascii: bool
) -> None:
    synthetic_values["configuration_id"] = "  synthetic-हिन्दी-🌾  "
    payload = json.dumps(synthetic_values, ensure_ascii=ensure_ascii).encode("utf-8")

    configuration = parse_inspection_configuration_json(payload)

    assert configuration.configuration_id == "synthetic-हिन्दी-🌾"


def test_parser_returns_immutable_nested_configuration(synthetic_json: bytes) -> None:
    configuration = parse_inspection_configuration_json(synthetic_json)

    with pytest.raises(ValidationError, match="frozen_instance"):
        _set_attribute(configuration, "configuration_version", "changed")
    with pytest.raises(ValidationError, match="frozen_instance"):
        _set_attribute(configuration.survey, "altitude_agl_m", 1)
    with pytest.raises(ValidationError):
        configuration.model_copy(update={"revisit": {"altitude_agl_m": 12, "speed_m_s": 4}})


def test_parser_accepts_exactly_the_byte_limit(synthetic_json: bytes) -> None:
    assert MAX_INSPECTION_CONFIGURATION_BYTES == 64 * 1024
    padded = synthetic_json + b" " * (MAX_INSPECTION_CONFIGURATION_BYTES - len(synthetic_json))

    assert len(padded) == MAX_INSPECTION_CONFIGURATION_BYTES
    assert parse_inspection_configuration_json(padded) == parse_inspection_configuration_json(
        synthetic_json
    )


def test_parser_rejects_one_byte_over_limit_before_decoding(synthetic_json: bytes) -> None:
    padded = synthetic_json + b" " * (MAX_INSPECTION_CONFIGURATION_BYTES - len(synthetic_json))

    _assert_parser_failure(padded + b"\xff", "input_too_large")


def test_size_limit_counts_utf8_bytes_not_characters(synthetic_values: dict[str, object]) -> None:
    synthetic_values["configuration_id"] = "🌾" * (MAX_INSPECTION_CONFIGURATION_BYTES // 3)
    content = json.dumps(synthetic_values, ensure_ascii=False)
    assert len(content) < MAX_INSPECTION_CONFIGURATION_BYTES
    assert len(content.encode("utf-8")) > MAX_INSPECTION_CONFIGURATION_BYTES

    _assert_parser_failure(content.encode("utf-8"), "input_too_large")


@pytest.mark.parametrize("invalid_payload", [None, "{}", bytearray(b"{}"), memoryview(b"{}"), 1])
def test_parser_requires_bytes(invalid_payload: object) -> None:
    _assert_parser_failure(cast(bytes, invalid_payload), "invalid_input")


@pytest.mark.parametrize("payload", [b"\xff", b'{"key":"\xc3"}', b"\xff\xfe{\x00}\x00"])
def test_parser_rejects_invalid_utf8(payload: bytes) -> None:
    _assert_parser_failure(payload, "invalid_encoding")


@pytest.mark.parametrize(
    "payload",
    [
        b'{"configuration_id":"\\ud800"}',
        b'{"configuration_id":"\\udfff"}',
        b'{"configuration_id":"\\ud800\\ud800"}',
        b'{"\\ud800":"value"}',
        b'{"survey":{"\\udfff":"value"}}',
        b'{"unknown":["\\ud800"]}',
        b'{"unknown":[["\\udfff"]]}',
        b'{"unknown":[{"\\ud800":"value"}]}',
    ],
    ids=[
        "high-surrogate",
        "low-surrogate",
        "two-high-surrogates",
        "root-key",
        "nested-key",
        "list-item",
        "nested-list-item",
        "key-inside-list",
    ],
)
def test_parser_rejects_unpaired_surrogate_escapes(payload: bytes) -> None:
    _assert_parser_failure(payload, "invalid_encoding")


def test_parser_accepts_valid_paired_surrogate_escapes(synthetic_values: dict[str, object]) -> None:
    synthetic_values["configuration_id"] = "synthetic-🌾"
    payload = json.dumps(synthetic_values, ensure_ascii=True).encode("utf-8")
    assert b"\\ud83c\\udf3e" in payload

    configuration = parse_inspection_configuration_json(payload)

    assert configuration.configuration_id == "synthetic-🌾"
    assert configuration.model_dump_json().encode("utf-8")


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b" \r\n\t",
        b"{",
        b"{'configuration_id': 'single-quotes'}",
        b'{"key": 1,}',
        b'{"key": 1} {"key": 2}',
        b'{"key": 1} trailing-data',
        b'{"key": 1 // comment\n}',
        b'{"key": "unescaped\x01control"}',
        b"\xef\xbb\xbf{}",
        b"configuration_id: synthetic-yaml-input",
        b"[" * 2000 + b"0" + b"]" * 2000,
        b'{"key":' + b"9" * 5000 + b"}",
    ],
    ids=[
        "empty",
        "whitespace",
        "unfinished-object",
        "single-quotes",
        "trailing-comma",
        "multiple-documents",
        "trailing-content",
        "comments",
        "control-character",
        "utf8-bom",
        "no-yaml-fallback",
        "excessive-nesting",
        "integer-decoding-limit",
    ],
)
def test_parser_rejects_malformed_or_unprocessable_json(payload: bytes) -> None:
    _assert_parser_failure(payload, "invalid_json")


@pytest.mark.parametrize("payload", [b"[]", b'"string"', b"null", b"true", b"1", b"1.5"])
def test_parser_requires_object_root(payload: bytes) -> None:
    _assert_parser_failure(payload, "invalid_json")


@pytest.mark.parametrize(
    "payload",
    [
        b'{"configuration_id":"a","configuration_id":"b"}',
        b'{"configuration_id":"a","configuration_id":"a"}',
        b'{"survey":{"speed_m_s":1,"speed_m_s":2}}',
        b'{"unknown":[{"key":1,"key":2}]}',
        b'{"key":1,"\\u006bey":2}',
        b'{"unknown":{"nested":{"key":1,"key":2}}}',
    ],
    ids=["root", "same-value", "nested", "inside-array", "escaped-key", "deep-object"],
)
def test_parser_rejects_duplicate_keys_at_every_level(payload: bytes) -> None:
    _assert_parser_failure(payload, "duplicate_key")


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"-Infinity", b"1e400", b"-1e400"])
@pytest.mark.parametrize("nested", [False, True])
def test_parser_rejects_nonfinite_values_before_model_validation(
    token: bytes, nested: bool
) -> None:
    payload = b'{"unexpected": [' + token + b"]}" if nested else token

    _assert_parser_failure(payload, "nonfinite_number")


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        (None, "configuration_id", " "),
        (None, "configuration_version", True),
        (None, "operating_environment", "night"),
        (None, "schema_version", "2.0"),
        (None, "unexpected", "reject-extra-fields"),
        ("survey", "altitude_agl_m", "12"),
        ("survey", "speed_m_s", True),
        ("survey", "speed_m_s", 0),
        ("survey", "front_overlap_fraction", 1),
        ("survey", "side_overlap_fraction", -0.1),
        ("survey", "schema_version", "2.0"),
        ("revisit", "altitude_agl_m", 12),
        ("revisit", "altitude_agl_m", 13),
        ("revisit", "altitude_agl_m", None),
        ("revisit", "speed_m_s", -1),
    ],
)
def test_parser_applies_existing_domain_validation(
    synthetic_values: dict[str, object], section: str | None, field: str, value: object
) -> None:
    if section is None:
        synthetic_values[field] = value
    else:
        nested = cast(dict[str, object], synthetic_values[section])
        nested[field] = value

    _assert_parser_failure(json.dumps(synthetic_values).encode("utf-8"), "invalid_configuration")


@pytest.mark.parametrize(
    "field",
    ["configuration_id", "configuration_version", "operating_environment", "survey", "revisit"],
)
def test_parser_never_supplies_missing_configuration_inputs(
    synthetic_values: dict[str, object], field: str
) -> None:
    del synthetic_values[field]

    _assert_parser_failure(json.dumps(synthetic_values).encode("utf-8"), "invalid_configuration")


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        (b'{"secret-field-92": 1,"secret-field-92":2}', "duplicate_key"),
        (b'{"configuration_id":"secret-field-92"}', "invalid_configuration"),
        (b'{"secret-field-92":', "invalid_json"),
        (b'{"secret-field-92":"\xff"}', "invalid_encoding"),
        (b'{"secret-field-92":NaN}', "nonfinite_number"),
    ],
)
def test_parser_errors_hide_inputs_and_original_exception_tracebacks(
    payload: bytes, reason: str
) -> None:
    error = _assert_parser_failure(payload, reason)

    assert "secret-field-92" not in str(error)
    assert "secret-field-92" not in repr(error.context)
    formatted = "".join(traceback.format_exception(error))
    assert "secret-field-92" not in formatted
    assert "JSONDecodeError" not in formatted
    assert "UnicodeDecodeError" not in formatted
    assert "ValidationError" not in formatted
    assert error.__cause__ is None


def test_parser_has_no_logging_side_effects(
    synthetic_json: bytes,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parse_inspection_configuration_json(synthetic_json)
    _assert_parser_failure(b'{"synthetic-private-value":', "invalid_json")

    assert caplog.records == []
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
