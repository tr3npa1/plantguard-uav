"""Read-only source boundary for inspection flight parameters."""

from typing import Protocol

from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration


class InspectionConfigurationSource(Protocol):
    """Supply a configuration without exposing its storage mechanism to a service."""

    def load(self) -> InspectionFlightConfiguration:
        """Read the current configured input or raise a controlled configuration error."""
        ...
