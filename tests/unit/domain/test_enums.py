from enum import StrEnum
import json

import pytest

from plantguard_uav.domain.enums import (
    FinalSiteStatus,
    ImageQualityStatus,
    MissionActivity,
    MissionWorkflowState,
    PreflightResult,
    ProcessingJobState,
    ReasonCode,
    RevisitStatus,
    SafetySeverity,
    SurveyHealthStatus,
    VehicleOperationalState,
)

EXPECTED_ENUM_VALUES: dict[type[StrEnum], tuple[str, ...]] = {
    MissionWorkflowState: (
        "created",
        "preparing",
        "awaiting_operator_approval",
        "ready",
        "active",
        "post_flight_processing",
        "report_ready",
        "complete",
        "aborted",
        "failed",
    ),
    MissionActivity: (
        "configuration",
        "technical_preflight",
        "takeoff",
        "survey",
        "same_flight_decision",
        "revisit",
        "return_home",
        "landing",
        "none",
    ),
    VehicleOperationalState: (
        "unknown",
        "disconnected",
        "on_ground",
        "armed",
        "taking_off",
        "in_flight",
        "holding",
        "returning_home",
        "landing",
        "landed",
        "manual_control",
    ),
    ProcessingJobState: (
        "queued",
        "running",
        "retry_wait",
        "paused",
        "succeeded",
        "failed",
        "cancelled",
    ),
    ImageQualityStatus: (
        "accepted",
        "rejected_blur",
        "rejected_underexposure",
        "rejected_overexposure",
        "rejected_obstruction",
        "rejected_low_plant_visibility",
        "rejected_corrupt",
        "rejected_missing_metadata",
        "rejected_other",
    ),
    SurveyHealthStatus: ("healthy", "unhealthy", "uncertain", "not_evaluated"),
    RevisitStatus: (
        "not_required",
        "planned",
        "in_progress",
        "completed",
        "skipped_safety",
        "skipped_battery",
        "skipped_route_invalid",
        "skipped_weather",
        "capture_failed",
        "not_completed",
    ),
    FinalSiteStatus: (
        "healthy",
        "healthy_after_suspicious_survey",
        "unhealthy_disease_identified",
        "unhealthy_disease_uncertain",
        "health_status_unresolved",
        "manual_inspection_recommended",
        "revisit_not_completed",
    ),
    ReasonCode: (
        "insufficient_visual_resolution",
        "image_too_blurry",
        "image_underexposed",
        "image_overexposed",
        "lens_obstructed",
        "plant_region_too_small",
        "plant_not_visible",
        "health_confidence_too_low",
        "disease_confidence_too_low",
        "disease_classification_uncertain",
        "top_predictions_too_similar",
        "inconsistent_revisit_views",
        "unsupported_crop",
        "unsupported_condition",
        "revisit_capture_failed",
        "revisit_skipped_safety",
        "revisit_skipped_battery",
        "revisit_skipped_route_invalid",
        "revisit_skipped_weather",
        "manual_inspection_recommended",
    ),
    SafetySeverity: ("normal", "warning", "degraded", "return_required", "emergency"),
    PreflightResult: ("PASS", "WARNING", "BLOCKED"),
}


@pytest.mark.parametrize(("enum_type", "expected_values"), EXPECTED_ENUM_VALUES.items())
def test_enum_members_exactly_match_frozen_contracts(
    enum_type: type[StrEnum], expected_values: tuple[str, ...]
) -> None:
    members = tuple(enum_type)

    assert tuple(member.value for member in members) == expected_values
    assert tuple(member.name for member in members) == tuple(
        value.upper() for value in expected_values
    )
    assert len(enum_type.__members__) == len(members)
    assert all(isinstance(member, str) for member in members)
    assert all(str(member) == member.value for member in members)
    assert json.loads(json.dumps(members[0])) == expected_values[0]


@pytest.mark.parametrize(("enum_type", "expected_values"), EXPECTED_ENUM_VALUES.items())
def test_enum_values_are_case_sensitive_and_fail_closed(
    enum_type: type[StrEnum], expected_values: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError, match="is not a valid"):
        enum_type("unknown_contract_value")

    with pytest.raises(ValueError, match="is not a valid"):
        enum_type(expected_values[0].swapcase())


def test_revisit_capture_failure_keeps_reason_and_final_status_distinct() -> None:
    assert ReasonCode("revisit_capture_failed") is ReasonCode.REVISIT_CAPTURE_FAILED
    assert RevisitStatus("capture_failed") is RevisitStatus.CAPTURE_FAILED
    assert FinalSiteStatus("revisit_not_completed") is FinalSiteStatus.REVISIT_NOT_COMPLETED

    with pytest.raises(ValueError, match="is not a valid"):
        FinalSiteStatus("revisit_capture_failed")
