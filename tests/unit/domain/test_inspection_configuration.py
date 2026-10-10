"""Synthetic contract examples only; these values are not approved flight settings."""

from decimal import Decimal
import json

from pydantic import ValidationError
import pytest

from plantguard_uav import domain
from plantguard_uav.domain.inspection_configuration import (
    InspectionFlightConfiguration,
    RevisitConfiguration,
    SurveyConfiguration,
)
from plantguard_uav.domain.value_objects import ContractModel


class FloatLike:
    def __float__(self) -> float:
        raise AssertionError("Configuration validation must not coerce arbitrary objects.")


def _survey_values() -> dict[str, object]:
    return {
        "altitude_agl_m": 12,
        "speed_m_s": 3,
        "front_overlap_fraction": 0.5,
        "side_overlap_fraction": 0.25,
    }


def _revisit_values() -> dict[str, object]:
    return {"altitude_agl_m": 6, "speed_m_s": 4}


def _configuration_values() -> dict[str, object]:
    return {
        "configuration_id": "synthetic-configuration",
        "configuration_version": "synthetic-revision-a",
        "operating_environment": "nominal_dry_daylight",
        "survey": _survey_values(),
        "revisit": _revisit_values(),
    }


def _model_values(model_type: type[ContractModel]) -> dict[str, object]:
    if model_type is SurveyConfiguration:
        return _survey_values()
    if model_type is RevisitConfiguration:
        return _revisit_values()
    return _configuration_values()


def _set_attribute(model: object, name: str, value: object) -> None:
    setattr(model, name, value)


MODELS = (SurveyConfiguration, RevisitConfiguration, InspectionFlightConfiguration)
NUMERIC_FIELDS = (
    (SurveyConfiguration, "altitude_agl_m"),
    (SurveyConfiguration, "speed_m_s"),
    (SurveyConfiguration, "front_overlap_fraction"),
    (SurveyConfiguration, "side_overlap_fraction"),
    (RevisitConfiguration, "altitude_agl_m"),
    (RevisitConfiguration, "speed_m_s"),
)


def test_configuration_models_are_publicly_exported() -> None:
    assert domain.SurveyConfiguration is SurveyConfiguration
    assert domain.RevisitConfiguration is RevisitConfiguration
    assert domain.InspectionFlightConfiguration is InspectionFlightConfiguration


def test_configuration_has_exact_nested_json_shape_and_round_trips() -> None:
    configuration = InspectionFlightConfiguration.model_validate(_configuration_values())
    expected = {
        **_configuration_values(),
        "survey": {**_survey_values(), "schema_version": "1.0"},
        "revisit": {**_revisit_values(), "schema_version": "1.0"},
        "schema_version": "1.0",
    }

    assert isinstance(configuration.survey, SurveyConfiguration)
    assert isinstance(configuration.revisit, RevisitConfiguration)
    assert configuration.model_dump(mode="json") == expected
    assert json.loads(configuration.model_dump_json()) == expected
    assert (
        InspectionFlightConfiguration.model_validate_json(configuration.model_dump_json())
        == configuration
    )
    for model in (configuration.survey, configuration.revisit):
        assert type(model.altitude_agl_m) is float
        assert type(model.speed_m_s) is float


def test_configuration_accepts_already_validated_nested_models() -> None:
    survey = SurveyConfiguration.model_validate(_survey_values())
    revisit = RevisitConfiguration.model_validate(_revisit_values())

    configuration = InspectionFlightConfiguration.model_validate(
        {**_configuration_values(), "survey": survey, "revisit": revisit}
    )

    assert configuration.survey == survey
    assert configuration.revisit == revisit


@pytest.mark.parametrize(
    ("model_type", "field_name"),
    [(model_type, name) for model_type in MODELS for name in _model_values(model_type)],
)
def test_every_configuration_input_except_schema_version_is_required(
    model_type: type[ContractModel], field_name: str
) -> None:
    values = _model_values(model_type)
    del values[field_name]

    with pytest.raises(ValidationError):
        model_type.model_validate(values)


@pytest.mark.parametrize(("model_type", "field_name"), NUMERIC_FIELDS)
@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        False,
        "0.5",
        b"0.5",
        None,
        Decimal("0.5"),
        [],
        {},
        FloatLike(),
        float("nan"),
        float("inf"),
        float("-inf"),
        pytest.param(10**400, id="overflowing-positive-integer"),
        pytest.param(-(10**400), id="overflowing-negative-integer"),
    ],
)
def test_numeric_fields_reject_coercion_nonfinite_values_and_overflow(
    model_type: type[ContractModel], field_name: str, invalid_value: object
) -> None:
    with pytest.raises(ValidationError):
        model_type.model_validate({**_model_values(model_type), field_name: invalid_value})


@pytest.mark.parametrize("model_type", [SurveyConfiguration, RevisitConfiguration])
@pytest.mark.parametrize("field_name", ["altitude_agl_m", "speed_m_s"])
@pytest.mark.parametrize("invalid_value", [0, -0.0, -0.001, -1])
def test_altitude_and_speed_must_be_positive(
    model_type: type[ContractModel], field_name: str, invalid_value: object
) -> None:
    with pytest.raises(ValidationError):
        model_type.model_validate({**_model_values(model_type), field_name: invalid_value})


@pytest.mark.parametrize("model_type", [SurveyConfiguration, RevisitConfiguration])
@pytest.mark.parametrize("field_name", ["altitude_agl_m", "speed_m_s"])
@pytest.mark.parametrize("valid_value", [0.001, 1, 1.5])
def test_positive_numeric_inputs_do_not_require_a_production_preset(
    model_type: type[ContractModel], field_name: str, valid_value: int | float
) -> None:
    model = model_type.model_validate({**_model_values(model_type), field_name: valid_value})

    assert model.model_dump()[field_name] == float(valid_value)


@pytest.mark.parametrize("field_name", ["front_overlap_fraction", "side_overlap_fraction"])
@pytest.mark.parametrize("invalid_value", [-0.001, 1, 1.001])
def test_overlap_rejects_values_outside_its_half_open_interval(
    field_name: str, invalid_value: int | float
) -> None:
    with pytest.raises(ValidationError):
        SurveyConfiguration.model_validate({**_survey_values(), field_name: invalid_value})


@pytest.mark.parametrize("field_name", ["front_overlap_fraction", "side_overlap_fraction"])
@pytest.mark.parametrize("valid_value", [0, 0.5, 0.999999])
def test_overlap_accepts_zero_and_values_strictly_below_one(
    field_name: str, valid_value: int | float
) -> None:
    survey = SurveyConfiguration.model_validate({**_survey_values(), field_name: valid_value})

    assert survey.model_dump()[field_name] == float(valid_value)


@pytest.mark.parametrize("model_type", MODELS)
@pytest.mark.parametrize(
    "invalid_values",
    [{"unexpected": True}, {"schema_version": "2.0"}, {"schema_version": 1.0}],
)
def test_models_reject_unknown_fields_and_unsupported_schema_versions(
    model_type: type[ContractModel], invalid_values: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model_type.model_validate({**_model_values(model_type), **invalid_values})


@pytest.mark.parametrize("field_name", ["configuration_id", "configuration_version"])
@pytest.mark.parametrize("invalid_value", ["", " \t ", b"revision", 1, None])
def test_configuration_requires_nonblank_strict_string_identifiers(
    field_name: str, invalid_value: object
) -> None:
    with pytest.raises(ValidationError):
        InspectionFlightConfiguration.model_validate(
            {**_configuration_values(), field_name: invalid_value}
        )


def test_configuration_preserves_opaque_identifier_contents_and_trims_outer_spaces() -> None:
    configuration = InspectionFlightConfiguration.model_validate(
        {
            **_configuration_values(),
            "configuration_id": "  synthetic config/alpha?trial=1  ",
            "configuration_version": "  revision beta  ",
        }
    )

    assert configuration.configuration_id == "synthetic config/alpha?trial=1"
    assert configuration.configuration_version == "revision beta"


@pytest.mark.parametrize(
    "environment",
    ["production", "night", "", "NOMINAL_DRY_DAYLIGHT", " nominal_dry_daylight ", None],
)
def test_configuration_rejects_unsupported_operating_environments(environment: object) -> None:
    with pytest.raises(ValidationError):
        InspectionFlightConfiguration.model_validate(
            {**_configuration_values(), "operating_environment": environment}
        )


@pytest.mark.parametrize("revisit_altitude", [12, 12.001, 13])
def test_revisit_altitude_must_be_strictly_lower_than_survey(revisit_altitude: int | float) -> None:
    with pytest.raises(ValidationError):
        InspectionFlightConfiguration.model_validate(
            {
                **_configuration_values(),
                "revisit": {**_revisit_values(), "altitude_agl_m": revisit_altitude},
            }
        )


def test_revisit_can_be_faster_than_survey_with_no_unapproved_speed_relationship() -> None:
    configuration = InspectionFlightConfiguration.model_validate(_configuration_values())

    assert configuration.revisit.altitude_agl_m < configuration.survey.altitude_agl_m
    assert configuration.revisit.speed_m_s > configuration.survey.speed_m_s


@pytest.mark.parametrize("field_name", ["survey", "revisit"])
@pytest.mark.parametrize("invalid_value", [None, [], "configuration", {}])
def test_configuration_requires_complete_nested_models(
    field_name: str, invalid_value: object
) -> None:
    with pytest.raises(ValidationError):
        InspectionFlightConfiguration.model_validate(
            {**_configuration_values(), field_name: invalid_value}
        )


@pytest.mark.parametrize("invalid_value", [True, "12"])
def test_json_input_does_not_bypass_numeric_type_validation(invalid_value: object) -> None:
    values = {
        **_configuration_values(),
        "survey": {**_survey_values(), "altitude_agl_m": invalid_value},
    }

    with pytest.raises(ValidationError):
        InspectionFlightConfiguration.model_validate_json(json.dumps(values))


@pytest.mark.parametrize("model_type", MODELS)
def test_all_configuration_models_are_frozen(model_type: type[ContractModel]) -> None:
    model = model_type.model_validate(_model_values(model_type))

    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(model, "schema_version", "2.0")


@pytest.mark.parametrize("deep", [False, True])
def test_copies_revalidate_nested_inputs_and_cross_field_rules(deep: bool) -> None:
    configuration = InspectionFlightConfiguration.model_validate(_configuration_values())

    copied = configuration.model_copy(
        update={"configuration_version": "  synthetic-revision-b  "}, deep=deep
    )

    assert copied is not configuration
    assert copied.configuration_version == "synthetic-revision-b"
    assert configuration.configuration_version == "synthetic-revision-a"
    assert copied.survey is not configuration.survey
    assert copied.revisit is not configuration.revisit
    assert copied.survey == configuration.survey
    with pytest.raises(ValidationError):
        configuration.model_copy(
            update={"revisit": {**_revisit_values(), "altitude_agl_m": 12}}, deep=deep
        )
    with pytest.raises(ValidationError):
        configuration.model_copy(
            update={"survey": {**_survey_values(), "speed_m_s": "3"}}, deep=deep
        )


@pytest.mark.parametrize("model_type", MODELS)
@pytest.mark.parametrize("invalid_values", [{"schema_version": "2.0"}, {"unexpected": True}])
def test_model_copy_does_not_bypass_version_and_extra_field_checks(
    model_type: type[ContractModel], invalid_values: dict[str, object]
) -> None:
    model = model_type.model_validate(_model_values(model_type))

    with pytest.raises(ValidationError):
        model.model_copy(update=invalid_values)


@pytest.mark.parametrize(
    ("field_name", "model_type"),
    [("survey", SurveyConfiguration), ("revisit", RevisitConfiguration)],
)
def test_unchecked_nested_instances_are_revalidated_in_parent_and_copies(
    field_name: str, model_type: type[ContractModel]
) -> None:
    unchecked = model_type.model_construct(
        _fields_set=None, **{**_model_values(model_type), "speed_m_s": 0}
    )
    configuration = InspectionFlightConfiguration.model_validate(_configuration_values())

    with pytest.raises(ValidationError):
        InspectionFlightConfiguration.model_validate(
            {**_configuration_values(), field_name: unchecked}
        )
    with pytest.raises(ValidationError):
        configuration.model_copy(update={field_name: unchecked})
    with pytest.raises(ValidationError):
        configuration.model_copy(update={field_name: unchecked}, deep=True)


def test_unchecked_combined_instance_is_revalidated() -> None:
    unchecked = InspectionFlightConfiguration.model_construct(
        configuration_id="   ",
        configuration_version="synthetic-revision-a",
        operating_environment="nominal_dry_daylight",
        survey=SurveyConfiguration.model_validate(_survey_values()),
        revisit=RevisitConfiguration.model_validate(_revisit_values()),
    )

    with pytest.raises(ValidationError):
        InspectionFlightConfiguration.model_validate(unchecked)
