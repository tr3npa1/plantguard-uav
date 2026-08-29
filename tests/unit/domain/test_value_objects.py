from datetime import UTC, datetime, timedelta, timezone

from pydantic import TypeAdapter, ValidationError
import pytest

from plantguard_uav.domain.value_objects import (
    SCHEMA_VERSION,
    ContractModel,
    NonBlankText,
    OpaqueIdentifier,
    SchemaVersion,
    UtcDateTime,
)


class ExampleContract(ContractModel):
    identifier: OpaqueIdentifier
    label: NonBlankText
    occurred_at: UtcDateTime
    schema_version: SchemaVersion = SCHEMA_VERSION


IDENTIFIER_ADAPTER: TypeAdapter[OpaqueIdentifier] = TypeAdapter(OpaqueIdentifier)
TEXT_ADAPTER: TypeAdapter[NonBlankText] = TypeAdapter(NonBlankText)
UTC_DATETIME_ADAPTER: TypeAdapter[UtcDateTime] = TypeAdapter(UtcDateTime)


def _set_attribute(instance: object, attribute: str, value: object) -> None:
    setattr(instance, attribute, value)


def test_nonblank_values_are_trimmed_and_whitespace_only_values_are_rejected() -> None:
    assert IDENTIFIER_ADAPTER.validate_python("  mission_01  ") == "mission_01"
    assert TEXT_ADAPTER.validate_python("  survey screening  ") == "survey screening"

    for adapter in (IDENTIFIER_ADAPTER, TEXT_ADAPTER):
        with pytest.raises(ValidationError):
            adapter.validate_python("   ")


def test_nonblank_values_reject_bytes_instead_of_coercing_them() -> None:
    for adapter in (IDENTIFIER_ADAPTER, TEXT_ADAPTER):
        with pytest.raises(ValidationError):
            adapter.validate_python(b"mission_01")


def test_aware_datetime_is_converted_to_utc_without_changing_the_instant() -> None:
    local_timezone = timezone(timedelta(hours=5, minutes=30))
    local_time = datetime(2026, 8, 19, 17, 30, tzinfo=local_timezone)

    normalised = UTC_DATETIME_ADAPTER.validate_python(local_time)

    assert normalised == datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    assert normalised.tzinfo is UTC


def test_timestamp_without_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        UTC_DATETIME_ADAPTER.validate_python("2026-08-19T12:00:00")


@pytest.mark.parametrize("numeric_timestamp", [0, 1_755_604_800.0])
def test_numeric_timestamp_is_rejected_as_ambiguous(numeric_timestamp: int | float) -> None:
    with pytest.raises(ValidationError, match="datetime objects or ISO 8601 strings"):
        UTC_DATETIME_ADAPTER.validate_python(numeric_timestamp)


def test_contract_defaults_to_schema_version_one_and_serializes_as_json() -> None:
    contract = ExampleContract(
        identifier="mission_01",
        label="survey",
        occurred_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
    )

    assert contract.schema_version == "1.0"
    assert contract.model_dump(mode="json") == {
        "identifier": "mission_01",
        "label": "survey",
        "occurred_at": "2026-08-19T12:00:00Z",
        "schema_version": "1.0",
    }


def test_unsupported_schema_version_and_extra_fields_are_rejected() -> None:
    valid_values = {
        "identifier": "mission_01",
        "label": "survey",
        "occurred_at": "2026-08-19T12:00:00Z",
    }

    with pytest.raises(ValidationError):
        ExampleContract.model_validate({**valid_values, "schema_version": "2.0"})

    with pytest.raises(ValidationError):
        ExampleContract.model_validate({**valid_values, "unexpected": True})


def test_contract_is_immutable_after_validation() -> None:
    contract = ExampleContract(
        identifier="mission_01",
        label="survey",
        occurred_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(contract, "label", "changed")


def test_model_copy_revalidates_updates_instead_of_trusting_them() -> None:
    contract = ExampleContract(
        identifier="mission_01",
        label="survey",
        occurred_at=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
    )

    unchanged = contract.model_copy()
    updated = contract.model_copy(update={"label": "  revisit  "}, deep=True)

    assert unchanged == contract
    assert unchanged is not contract
    assert updated is not contract
    assert updated.label == "revisit"
    with pytest.raises(ValidationError):
        contract.model_copy(update={"schema_version": "2.0"})
