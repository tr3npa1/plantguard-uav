"""Immutable snapshots for separately owned PlantGuard UAV state dimensions."""

from plantguard_uav.domain.enums import (
    MissionActivity,
    MissionWorkflowState,
    ProcessingJobState,
    ReasonCode,
    VehicleOperationalState,
)
from plantguard_uav.domain.value_objects import (
    SCHEMA_VERSION,
    ContractModel,
    NonBlankText,
    OpaqueIdentifier,
    SchemaVersion,
    UtcDateTime,
)


class MissionStateSnapshot(ContractModel):
    """Record workflow state and activity owned by the Mission Orchestrator."""

    mission_id: OpaqueIdentifier
    workflow_state: MissionWorkflowState
    activity: MissionActivity
    recorded_at: UtcDateTime
    schema_version: SchemaVersion = SCHEMA_VERSION


class VehicleStateSnapshot(ContractModel):
    """Record vehicle state reported by the Vehicle Adapter for one mission."""

    mission_id: OpaqueIdentifier
    operational_state: VehicleOperationalState
    recorded_at: UtcDateTime
    schema_version: SchemaVersion = SCHEMA_VERSION


class ProcessingJobStateSnapshot(ContractModel):
    """Record independently owned background-job state and optional mission context."""

    job_id: OpaqueIdentifier
    mission_id: OpaqueIdentifier | None = None
    processing_state: ProcessingJobState
    recorded_at: UtcDateTime
    schema_version: SchemaVersion = SCHEMA_VERSION


class DecisionReason(ContractModel):
    """Explain a withheld, uncertain, or degraded result with traceable evidence."""

    reason_code: ReasonCode
    explanation: NonBlankText
    evidence_references: tuple[OpaqueIdentifier, ...] = ()
    stage: NonBlankText
    occurred_at: UtcDateTime
    schema_version: SchemaVersion = SCHEMA_VERSION
