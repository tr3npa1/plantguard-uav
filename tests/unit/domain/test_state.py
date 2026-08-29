from datetime import UTC, datetime

from pydantic import ValidationError
import pytest

from plantguard_uav.domain import (
    DecisionReason,
    MissionActivity,
    MissionStateSnapshot,
    MissionWorkflowState,
    ProcessingJobState,
    ProcessingJobStateSnapshot,
    ReasonCode,
    VehicleOperationalState,
    VehicleStateSnapshot,
)
from plantguard_uav.domain.value_objects import ContractModel

RECORDED_AT = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def _set_attribute(instance: object, attribute: str, value: object) -> None:
    setattr(instance, attribute, value)


def test_state_snapshots_keep_ownership_dimensions_separate() -> None:
    mission = MissionStateSnapshot(
        mission_id="mission_01",
        workflow_state=MissionWorkflowState.ACTIVE,
        activity=MissionActivity.SURVEY,
        recorded_at=RECORDED_AT,
    )
    vehicle = VehicleStateSnapshot(
        mission_id="mission_01",
        operational_state=VehicleOperationalState.IN_FLIGHT,
        recorded_at=RECORDED_AT,
    )
    job = ProcessingJobStateSnapshot(
        job_id="job_01",
        mission_id="mission_01",
        processing_state=ProcessingJobState.RUNNING,
        recorded_at=RECORDED_AT,
    )

    assert type(mission.workflow_state) is MissionWorkflowState
    assert type(mission.activity) is MissionActivity
    assert type(vehicle.operational_state) is VehicleOperationalState
    assert type(job.processing_state) is ProcessingJobState


def test_state_snapshot_serializes_with_contract_strings_and_utc_time() -> None:
    snapshot = MissionStateSnapshot(
        mission_id="mission_01",
        workflow_state=MissionWorkflowState.POST_FLIGHT_PROCESSING,
        activity=MissionActivity.RETURN_HOME,
        recorded_at=RECORDED_AT,
    )

    assert snapshot.model_dump(mode="json") == {
        "mission_id": "mission_01",
        "workflow_state": "post_flight_processing",
        "activity": "return_home",
        "recorded_at": "2026-08-19T12:00:00Z",
        "schema_version": "1.0",
    }


@pytest.mark.parametrize(
    ("model_type", "raw_values"),
    [
        (
            MissionStateSnapshot,
            {
                "mission_id": "mission_01",
                "workflow_state": "in_flight",
                "activity": "survey",
                "recorded_at": "2026-08-19T12:00:00Z",
            },
        ),
        (
            VehicleStateSnapshot,
            {
                "mission_id": "mission_01",
                "operational_state": "active",
                "recorded_at": "2026-08-19T12:00:00Z",
            },
        ),
        (
            ProcessingJobStateSnapshot,
            {
                "job_id": "job_01",
                "processing_state": "complete",
                "recorded_at": "2026-08-19T12:00:00Z",
            },
        ),
    ],
)
def test_state_snapshots_reject_values_from_other_dimensions(
    model_type: type[ContractModel], raw_values: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model_type.model_validate(raw_values)


def test_processing_snapshot_allows_a_job_without_mission_context() -> None:
    snapshot = ProcessingJobStateSnapshot(
        job_id="maintenance_job_01",
        processing_state=ProcessingJobState.QUEUED,
        recorded_at=RECORDED_AT,
    )

    assert snapshot.mission_id is None


def test_decision_reason_is_traceable_and_converts_evidence_to_a_tuple() -> None:
    reason = DecisionReason.model_validate(
        {
            "reason_code": "health_confidence_too_low",
            "explanation": "Evidence did not meet the configured health threshold.",
            "evidence_references": ["image_01", "observation_01"],
            "stage": "survey_screening",
            "occurred_at": "2026-08-19T17:30:00+05:30",
        }
    )

    assert reason.reason_code is ReasonCode.HEALTH_CONFIDENCE_TOO_LOW
    assert reason.evidence_references == ("image_01", "observation_01")
    assert reason.occurred_at == RECORDED_AT
    assert reason.model_dump(mode="json")["occurred_at"] == "2026-08-19T12:00:00Z"


@pytest.mark.parametrize(
    "overrides",
    [
        {"explanation": "   "},
        {"stage": "   "},
        {"evidence_references": ["image_01", "   "]},
        {"reason_code": "unknown_reason"},
    ],
)
def test_decision_reason_rejects_incomplete_or_unknown_values(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "reason_code": "revisit_capture_failed",
        "explanation": "The revisit image could not be captured.",
        "evidence_references": [],
        "stage": "revisit_capture",
        "occurred_at": "2026-08-19T12:00:00Z",
    }
    values.update(overrides)

    with pytest.raises(ValidationError):
        DecisionReason.model_validate(values)


@pytest.mark.parametrize(
    "contract",
    [
        MissionStateSnapshot(
            mission_id="mission_01",
            workflow_state=MissionWorkflowState.ACTIVE,
            activity=MissionActivity.SURVEY,
            recorded_at=RECORDED_AT,
        ),
        VehicleStateSnapshot(
            mission_id="mission_01",
            operational_state=VehicleOperationalState.IN_FLIGHT,
            recorded_at=RECORDED_AT,
        ),
        ProcessingJobStateSnapshot(
            job_id="job_01",
            processing_state=ProcessingJobState.RUNNING,
            recorded_at=RECORDED_AT,
        ),
        DecisionReason(
            reason_code=ReasonCode.REVISIT_CAPTURE_FAILED,
            explanation="Capture failed.",
            stage="revisit_capture",
            occurred_at=RECORDED_AT,
        ),
    ],
)
def test_state_contracts_are_immutable(contract: ContractModel) -> None:
    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(contract, "schema_version", "2.0")
