"""Application-specific exceptions for PlantGuard UAV."""

from collections.abc import Mapping
from typing import Literal

type InspectionConfigurationFailureReason = Literal[
    "invalid_input",
    "file_unavailable",
    "not_regular_file",
    "input_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "nonfinite_number",
    "invalid_configuration",
    "identity_mismatch",
]


class PlantGuardError(Exception):
    """Base class for errors that may be handled predictably by the application."""

    error_code = "plantguard_error"
    status_code = 500

    def __init__(
        self,
        public_message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        """Create an error with a safe public message and private structured context."""
        super().__init__(public_message)
        self.public_message = public_message
        self.context = dict(context or {})


class ConfigurationError(PlantGuardError):
    """Report that application configuration could not be loaded safely."""

    error_code = "configuration_error"


class InspectionConfigurationError(ConfigurationError):
    """Report an inspection-input failure without exposing its contents or path."""

    def __init__(self, *, reason: InspectionConfigurationFailureReason) -> None:
        """Create a fixed public error with only a controlled failure category."""
        super().__init__(
            "Inspection configuration could not be loaded.",
            context={"operation": "load_inspection_configuration", "reason": reason},
        )


class InspectionConfigurationUnavailableError(ConfigurationError):
    """Report absent server-side source wiring without exposing deployment details."""

    status_code = 503

    def __init__(self) -> None:
        """Create a fixed unavailable response with a controlled internal reason."""
        super().__init__(
            "Inspection configuration source is not configured.",
            context={
                "operation": "load_inspection_configuration",
                "reason": "source_not_configured",
            },
        )


class StartupError(PlantGuardError):
    """Report that an application service could not complete startup."""

    error_code = "startup_error"


class PersistenceError(PlantGuardError):
    """Report a structured-storage failure without exposing adapter details."""

    error_code = "persistence_error"

    def __init__(self, *, context: Mapping[str, object] | None = None) -> None:
        """Create a persistence error with a fixed, safe public message."""
        super().__init__(
            "Persistent storage operation could not be completed.",
            context=context,
        )


class FieldNotFoundError(PlantGuardError):
    """Report that no authoritative saved-field definition matches a query."""

    error_code = "not_found"
    status_code = 404

    def __init__(self, *, context: Mapping[str, object] | None = None) -> None:
        """Create a not-found error without exposing identifiers in its public message."""
        super().__init__(
            "The requested saved field sector was not found.",
            context=context,
        )
