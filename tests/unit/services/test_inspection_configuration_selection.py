"""Selection examples are synthetic inputs, never approved flight profiles."""

from inspect import iscoroutinefunction, signature
import traceback
from typing import cast

from pydantic import ValidationError
import pytest

from plantguard_uav.domain.inspection_configuration import (
    InspectionFlightConfiguration,
    RevisitConfiguration,
    SurveyConfiguration,
)
from plantguard_uav.domain.value_objects import ContractModel
from plantguard_uav.errors import ConfigurationError, InspectionConfigurationError
from plantguard_uav.repositories import InspectionConfigurationSource as ExportedSource
from plantguard_uav.repositories.inspection_configuration import InspectionConfigurationSource
from plantguard_uav.services import (
    GetInspectionConfigurationQuery as ExportedQuery,
    GetInspectionConfigurationService as ExportedService,
)
from plantguard_uav.services.inspection_configuration import (
    GetInspectionConfigurationQuery,
    GetInspectionConfigurationService,
)


class FakeConfigurationSource:
    def __init__(self, results: list[object]) -> None:
        self._results = results.copy()
        self.calls = 0

    def load(self) -> InspectionFlightConfiguration:
        self.calls += 1
        return cast(InspectionFlightConfiguration, self._results.pop(0))


class FailingConfigurationSource:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def load(self) -> InspectionFlightConfiguration:
        self.calls += 1
        raise self.error


@pytest.fixture
def synthetic_values() -> dict[str, object]:
    return {
        "configuration_id": "synthetic-selection-test",
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
def synthetic_configuration(synthetic_values: dict[str, object]) -> InspectionFlightConfiguration:
    return InspectionFlightConfiguration.model_validate(synthetic_values)


def _query(**updates: object) -> GetInspectionConfigurationQuery:
    values: dict[str, object] = {
        "configuration_id": "synthetic-selection-test",
        "configuration_version": "synthetic-revision-a",
    }
    values.update(updates)
    return GetInspectionConfigurationQuery.model_validate(values)


def _set_attribute(instance: object, name: str, value: object) -> None:
    setattr(instance, name, value)


def _unchecked_model[Model: ContractModel](model: type[Model], values: dict[str, object]) -> Model:
    return cast(Model, model.model_construct(_fields_set=None, **values))


def _assert_failure(error: InspectionConfigurationError, reason: str) -> None:
    assert isinstance(error, ConfigurationError)
    assert error.error_code == "configuration_error"
    assert error.public_message == "Inspection configuration could not be loaded."
    assert str(error) == error.public_message
    assert error.context == {"operation": "load_inspection_configuration", "reason": reason}


def test_selection_components_are_exported_and_source_contract_is_synchronous() -> None:
    assert ExportedSource is InspectionConfigurationSource
    assert ExportedQuery is GetInspectionConfigurationQuery
    assert ExportedService is GetInspectionConfigurationService
    assert tuple(signature(InspectionConfigurationSource.load).parameters) == ("self",)
    assert not iscoroutinefunction(InspectionConfigurationSource.load)
    assert not iscoroutinefunction(GetInspectionConfigurationService.execute)


def test_selection_query_is_required_versioned_and_frozen() -> None:
    query = _query()

    assert query.model_dump(mode="json") == {
        "configuration_id": "synthetic-selection-test",
        "configuration_version": "synthetic-revision-a",
        "schema_version": "1.0",
    }
    with pytest.raises(ValidationError, match="frozen_instance"):
        _set_attribute(query, "configuration_version", "changed")


@pytest.mark.parametrize("field", ["configuration_id", "configuration_version"])
@pytest.mark.parametrize("value", ["", " \t\n", None, True, 1, 1.5, b"profile", [], {}])
def test_selection_query_rejects_blank_and_non_string_identity(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _query(**{field: value})


@pytest.mark.parametrize("field", ["configuration_id", "configuration_version"])
def test_selection_query_requires_each_identity_field(field: str) -> None:
    values = _query().model_dump()
    del values[field]

    with pytest.raises(ValidationError):
        GetInspectionConfigurationQuery.model_validate(values)


@pytest.mark.parametrize("value", [None, "2.0", " 1.0 ", 1, 1.0, True])
def test_selection_query_rejects_unsupported_schema_version(value: object) -> None:
    with pytest.raises(ValidationError):
        _query(schema_version=value)


def test_selection_query_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _query(file_path="not-a-query-field.json")


def test_selection_query_normalizes_only_outer_whitespace() -> None:
    query = _query(configuration_id="  Synthetic FIELD 🌾  ", configuration_version="  REV A  ")

    assert query.configuration_id == "Synthetic FIELD 🌾"
    assert query.configuration_version == "REV A"


@pytest.mark.parametrize("deep", [False, True])
def test_selection_query_copy_revalidates_and_preserves_original(deep: bool) -> None:
    query = _query()

    copied = query.model_copy(
        update={"configuration_version": "  synthetic-revision-b  "}, deep=deep
    )

    assert copied.configuration_version == "synthetic-revision-b"
    assert query.configuration_version == "synthetic-revision-a"
    assert copied is not query
    with pytest.raises(ValidationError):
        query.model_copy(update={"configuration_id": False}, deep=deep)
    with pytest.raises(ValidationError):
        query.model_copy(update={"schema_version": "2.0"}, deep=deep)


@pytest.mark.parametrize(
    "updates",
    [
        {"configuration_id": " "},
        {"configuration_version": 123},
        {"schema_version": "2.0"},
    ],
)
def test_selection_service_revalidates_unchecked_query_before_reading(
    updates: dict[str, object], synthetic_configuration: InspectionFlightConfiguration
) -> None:
    values = _query().model_dump()
    values.update(updates)
    unchecked = _unchecked_model(GetInspectionConfigurationQuery, values)
    source = FakeConfigurationSource([synthetic_configuration])

    with pytest.raises(ValidationError):
        GetInspectionConfigurationService(source).execute(unchecked)

    assert source.calls == 0


def test_selection_service_rejects_incomplete_unchecked_query_before_reading(
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    unchecked = _unchecked_model(GetInspectionConfigurationQuery, {"configuration_id": "synthetic"})
    source = FakeConfigurationSource([synthetic_configuration])

    with pytest.raises(ValidationError):
        GetInspectionConfigurationService(source).execute(unchecked)

    assert source.calls == 0


@pytest.mark.parametrize("value", [None, "not-a-query", 42, []])
def test_selection_service_rejects_invalid_runtime_query_before_reading(
    value: object, synthetic_configuration: InspectionFlightConfiguration
) -> None:
    source = FakeConfigurationSource([synthetic_configuration])

    with pytest.raises(ValidationError):
        GetInspectionConfigurationService(source).execute(
            cast(GetInspectionConfigurationQuery, value)
        )

    assert source.calls == 0


def test_selection_service_returns_matching_configuration_without_changing_inputs(
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    query = _query()
    original_configuration = synthetic_configuration.model_dump(round_trip=True)
    original_query = query.model_dump(round_trip=True)
    fake = FakeConfigurationSource([synthetic_configuration])
    source: InspectionConfigurationSource = fake

    configuration = GetInspectionConfigurationService(source).execute(query)

    assert configuration == synthetic_configuration
    assert fake.calls == 1
    assert synthetic_configuration.model_dump(round_trip=True) == original_configuration
    assert query.model_dump(round_trip=True) == original_query
    with pytest.raises(ValidationError, match="frozen_instance"):
        _set_attribute(configuration, "configuration_id", "changed")
    with pytest.raises(ValidationError, match="frozen_instance"):
        _set_attribute(configuration.survey, "speed_m_s", 5)


def test_selection_service_normalizes_unchecked_query_before_comparing(
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    query = GetInspectionConfigurationQuery.model_construct(
        configuration_id="  synthetic-selection-test  ",
        configuration_version="  synthetic-revision-a  ",
    )
    source = FakeConfigurationSource([synthetic_configuration])

    result = GetInspectionConfigurationService(source).execute(query)

    assert result == synthetic_configuration
    assert query.configuration_id == "  synthetic-selection-test  "
    assert query.configuration_version == "  synthetic-revision-a  "
    assert source.calls == 1


@pytest.mark.parametrize(
    "query_updates",
    [
        {"configuration_id": "different-id"},
        {"configuration_version": "different-revision"},
        {"configuration_id": "different-id", "configuration_version": "different-revision"},
        {"configuration_id": "SYNTHETIC-SELECTION-TEST"},
        {"configuration_version": "SYNTHETIC-REVISION-A"},
        {"configuration_version": "latest"},
        {"configuration_version": "1.0"},
    ],
)
def test_selection_service_requires_exact_id_and_revision_without_special_aliases(
    query_updates: dict[str, object], synthetic_configuration: InspectionFlightConfiguration
) -> None:
    source = FakeConfigurationSource([synthetic_configuration])

    with pytest.raises(InspectionConfigurationError) as caught:
        GetInspectionConfigurationService(source).execute(_query(**query_updates))

    _assert_failure(caught.value, "identity_mismatch")
    assert source.calls == 1


@pytest.mark.parametrize("identity", ["latest", "1.0", "Synthetic Profile 🌾"])
def test_selection_service_allows_any_matching_opaque_revision(
    identity: str, synthetic_configuration: InspectionFlightConfiguration
) -> None:
    configuration = synthetic_configuration.model_copy(update={"configuration_version": identity})
    source = FakeConfigurationSource([configuration])

    result = GetInspectionConfigurationService(source).execute(
        _query(configuration_version=identity)
    )

    assert result.configuration_version == identity


@pytest.mark.parametrize("value", [None, "not-a-configuration", 42, [], {}])
def test_selection_service_translates_invalid_source_values(value: object) -> None:
    source = FakeConfigurationSource([value])

    with pytest.raises(InspectionConfigurationError) as caught:
        GetInspectionConfigurationService(source).execute(_query())

    _assert_failure(caught.value, "invalid_configuration")
    assert source.calls == 1


@pytest.mark.parametrize(
    "updates",
    [
        {"configuration_id": " "},
        {"configuration_version": 4},
        {"operating_environment": "night"},
        {"schema_version": "2.0"},
        {"survey": _unchecked_model(SurveyConfiguration, {"altitude_agl_m": 0})},
        {"revisit": RevisitConfiguration.model_construct(altitude_agl_m=12, speed_m_s=4)},
        {
            "revisit": _unchecked_model(
                RevisitConfiguration, {"altitude_agl_m": 6, "speed_m_s": "4"}
            )
        },
        {"revisit": RevisitConfiguration.model_construct(altitude_agl_m=6, speed_m_s=float("nan"))},
    ],
)
def test_selection_service_revalidates_unchecked_configuration_and_nested_models(
    updates: dict[str, object], synthetic_configuration: InspectionFlightConfiguration
) -> None:
    values = {
        "configuration_id": synthetic_configuration.configuration_id,
        "configuration_version": synthetic_configuration.configuration_version,
        "operating_environment": synthetic_configuration.operating_environment,
        "survey": synthetic_configuration.survey,
        "revisit": synthetic_configuration.revisit,
    }
    values.update(updates)
    unchecked = _unchecked_model(InspectionFlightConfiguration, values)
    source = FakeConfigurationSource([unchecked])

    with pytest.raises(InspectionConfigurationError) as caught:
        GetInspectionConfigurationService(source).execute(_query())

    _assert_failure(caught.value, "invalid_configuration")
    assert source.calls == 1


def test_selection_service_revalidates_source_before_identity_comparison(
    synthetic_values: dict[str, object],
) -> None:
    synthetic_values["configuration_id"] = "wrong-id"
    synthetic_values["survey"] = {}
    source = FakeConfigurationSource(
        [_unchecked_model(InspectionFlightConfiguration, synthetic_values)]
    )

    with pytest.raises(InspectionConfigurationError) as caught:
        GetInspectionConfigurationService(source).execute(_query())

    _assert_failure(caught.value, "invalid_configuration")


def test_selection_service_normalizes_source_identity_without_mutating_original(
    synthetic_values: dict[str, object],
) -> None:
    synthetic_values["configuration_id"] = "  synthetic-selection-test  "
    unchecked = _unchecked_model(InspectionFlightConfiguration, synthetic_values)
    source = FakeConfigurationSource([unchecked])

    result = GetInspectionConfigurationService(source).execute(_query())

    assert result.configuration_id == "synthetic-selection-test"
    assert unchecked.configuration_id == "  synthetic-selection-test  "
    assert isinstance(result.survey, SurveyConfiguration)


def test_selection_service_reads_fresh_values_even_when_id_and_revision_stay_same(
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    changed = synthetic_configuration.model_copy(
        update={"revisit": {"altitude_agl_m": 6, "speed_m_s": 5}}
    )
    source = FakeConfigurationSource([synthetic_configuration, changed])
    service = GetInspectionConfigurationService(source)

    first = service.execute(_query())
    second = service.execute(_query())

    assert first.revisit.speed_m_s == 4
    assert second.revisit.speed_m_s == 5
    assert first.configuration_version == second.configuration_version
    assert source.calls == 2


def test_selection_service_does_not_fall_back_to_a_previous_matching_configuration(
    synthetic_configuration: InspectionFlightConfiguration,
) -> None:
    changed = synthetic_configuration.model_copy(update={"configuration_version": "revision-b"})
    source = FakeConfigurationSource([synthetic_configuration, changed])
    service = GetInspectionConfigurationService(source)
    assert service.execute(_query()) == synthetic_configuration

    with pytest.raises(InspectionConfigurationError) as caught:
        service.execute(_query())

    _assert_failure(caught.value, "identity_mismatch")
    assert source.calls == 2


def test_selection_service_propagates_source_configuration_error_unchanged() -> None:
    error = InspectionConfigurationError(reason="file_unavailable")
    source = FailingConfigurationSource(error)

    with pytest.raises(InspectionConfigurationError) as caught:
        GetInspectionConfigurationService(source).execute(_query())

    assert caught.value is error
    assert source.calls == 1


def test_selection_service_does_not_mask_unexpected_source_programming_errors() -> None:
    error = RuntimeError("synthetic-source-programming-error")
    source = FailingConfigurationSource(error)

    with pytest.raises(RuntimeError) as caught:
        GetInspectionConfigurationService(source).execute(_query())

    assert caught.value is error
    assert source.calls == 1


def test_selection_service_does_not_mislabel_source_validation_errors() -> None:
    with pytest.raises(ValidationError) as original:
        _query(configuration_id=None)
    source = FailingConfigurationSource(original.value)

    with pytest.raises(ValidationError) as caught:
        GetInspectionConfigurationService(source).execute(_query())

    assert caught.value is original.value


@pytest.mark.parametrize("invalid_model", [False, True])
def test_selection_failures_do_not_expose_identity_or_configuration_and_do_not_log(
    invalid_model: bool, synthetic_values: dict[str, object], caplog: pytest.LogCaptureFixture
) -> None:
    sentinel = "private-synthetic-selection-sentinel"
    synthetic_values["configuration_id"] = sentinel
    if invalid_model:
        synthetic_values["operating_environment"] = sentinel
    source = FakeConfigurationSource(
        [_unchecked_model(InspectionFlightConfiguration, synthetic_values)]
    )
    service = GetInspectionConfigurationService(source)
    caplog.clear()

    with pytest.raises(InspectionConfigurationError) as caught:
        service.execute(_query())

    _assert_failure(caught.value, "invalid_configuration" if invalid_model else "identity_mismatch")
    assert sentinel not in str(caught.value)
    assert sentinel not in repr(caught.value.context)
    assert sentinel not in "".join(traceback.format_exception(caught.value))
    assert not caplog.records
