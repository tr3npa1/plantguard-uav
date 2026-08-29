"""Canonical domain vocabulary frozen by the PlantGuard UAV contracts."""

from enum import StrEnum


class MissionWorkflowState(StrEnum):
    """Authoritative mission workflow states owned by the Mission Orchestrator."""

    CREATED = "created"
    PREPARING = "preparing"
    AWAITING_OPERATOR_APPROVAL = "awaiting_operator_approval"
    READY = "ready"
    ACTIVE = "active"
    POST_FLIGHT_PROCESSING = "post_flight_processing"
    REPORT_READY = "report_ready"
    COMPLETE = "complete"
    ABORTED = "aborted"
    FAILED = "failed"


class MissionActivity(StrEnum):
    """Current mission activities, kept separate from workflow state."""

    CONFIGURATION = "configuration"
    TECHNICAL_PREFLIGHT = "technical_preflight"
    TAKEOFF = "takeoff"
    SURVEY = "survey"
    SAME_FLIGHT_DECISION = "same_flight_decision"
    REVISIT = "revisit"
    RETURN_HOME = "return_home"
    LANDING = "landing"
    NONE = "none"


class VehicleOperationalState(StrEnum):
    """Vehicle states derived from PX4 through the Vehicle Adapter."""

    UNKNOWN = "unknown"
    DISCONNECTED = "disconnected"
    ON_GROUND = "on_ground"
    ARMED = "armed"
    TAKING_OFF = "taking_off"
    IN_FLIGHT = "in_flight"
    HOLDING = "holding"
    RETURNING_HOME = "returning_home"
    LANDING = "landing"
    LANDED = "landed"
    MANUAL_CONTROL = "manual_control"


class ProcessingJobState(StrEnum):
    """Background processing states owned by the responsible worker."""

    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageQualityStatus(StrEnum):
    """Canonical outcomes produced by image-quality validation."""

    ACCEPTED = "accepted"
    REJECTED_BLUR = "rejected_blur"
    REJECTED_UNDEREXPOSURE = "rejected_underexposure"
    REJECTED_OVEREXPOSURE = "rejected_overexposure"
    REJECTED_OBSTRUCTION = "rejected_obstruction"
    REJECTED_LOW_PLANT_VISIBILITY = "rejected_low_plant_visibility"
    REJECTED_CORRUPT = "rejected_corrupt"
    REJECTED_MISSING_METADATA = "rejected_missing_metadata"
    REJECTED_OTHER = "rejected_other"


class SurveyHealthStatus(StrEnum):
    """Health classifications permitted during survey screening."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNCERTAIN = "uncertain"
    NOT_EVALUATED = "not_evaluated"


class RevisitStatus(StrEnum):
    """Canonical states for a suspicious site's revisit attempt."""

    NOT_REQUIRED = "not_required"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED_SAFETY = "skipped_safety"
    SKIPPED_BATTERY = "skipped_battery"
    SKIPPED_ROUTE_INVALID = "skipped_route_invalid"
    SKIPPED_WEATHER = "skipped_weather"
    CAPTURE_FAILED = "capture_failed"
    NOT_COMPLETED = "not_completed"


class FinalSiteStatus(StrEnum):
    """Farmer-facing final outcomes for a suspicious site."""

    HEALTHY = "healthy"
    HEALTHY_AFTER_SUSPICIOUS_SURVEY = "healthy_after_suspicious_survey"
    UNHEALTHY_DISEASE_IDENTIFIED = "unhealthy_disease_identified"
    UNHEALTHY_DISEASE_UNCERTAIN = "unhealthy_disease_uncertain"
    HEALTH_STATUS_UNRESOLVED = "health_status_unresolved"
    MANUAL_INSPECTION_RECOMMENDED = "manual_inspection_recommended"
    REVISIT_NOT_COMPLETED = "revisit_not_completed"


class ReasonCode(StrEnum):
    """Machine-readable reasons for withheld, uncertain, or degraded outcomes."""

    INSUFFICIENT_VISUAL_RESOLUTION = "insufficient_visual_resolution"
    IMAGE_TOO_BLURRY = "image_too_blurry"
    IMAGE_UNDEREXPOSED = "image_underexposed"
    IMAGE_OVEREXPOSED = "image_overexposed"
    LENS_OBSTRUCTED = "lens_obstructed"
    PLANT_REGION_TOO_SMALL = "plant_region_too_small"
    PLANT_NOT_VISIBLE = "plant_not_visible"
    HEALTH_CONFIDENCE_TOO_LOW = "health_confidence_too_low"
    DISEASE_CONFIDENCE_TOO_LOW = "disease_confidence_too_low"
    DISEASE_CLASSIFICATION_UNCERTAIN = "disease_classification_uncertain"
    TOP_PREDICTIONS_TOO_SIMILAR = "top_predictions_too_similar"
    INCONSISTENT_REVISIT_VIEWS = "inconsistent_revisit_views"
    UNSUPPORTED_CROP = "unsupported_crop"
    UNSUPPORTED_CONDITION = "unsupported_condition"
    REVISIT_CAPTURE_FAILED = "revisit_capture_failed"
    REVISIT_SKIPPED_SAFETY = "revisit_skipped_safety"
    REVISIT_SKIPPED_BATTERY = "revisit_skipped_battery"
    REVISIT_SKIPPED_ROUTE_INVALID = "revisit_skipped_route_invalid"
    REVISIT_SKIPPED_WEATHER = "revisit_skipped_weather"
    MANUAL_INSPECTION_RECOMMENDED = "manual_inspection_recommended"


class SafetySeverity(StrEnum):
    """Canonical vocabulary for the severity of operational safety conditions."""

    NORMAL = "normal"
    WARNING = "warning"
    DEGRADED = "degraded"
    RETURN_REQUIRED = "return_required"
    EMERGENCY = "emergency"


class PreflightResult(StrEnum):
    """Canonical uppercase outcomes of an individual preflight check."""

    PASS = "PASS"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
