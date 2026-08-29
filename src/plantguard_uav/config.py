"""Validated, layered configuration for PlantGuard UAV."""

from collections.abc import Mapping
from enum import StrEnum
from importlib.resources import files
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    SettingsError,
    YamlConfigSettingsSource,
)
import yaml

from plantguard_uav.errors import ConfigurationError

LOCAL_DEFAULT_CONFIG_PATH = Path("configs/default.yaml")
PACKAGED_DEFAULT_CONFIG_PATH = Path(
    str(files("plantguard_uav").joinpath("configs", "default.yaml"))
)
ALLOWED_ENVIRONMENT_VARIABLES = frozenset(
    {
        "PLANTGUARD_API",
        "PLANTGUARD_API__HOST",
        "PLANTGUARD_API__PORT",
        "PLANTGUARD_DATABASE",
        "PLANTGUARD_DATABASE__CONNECT_TIMEOUT_SECONDS",
        "PLANTGUARD_DATABASE__URL",
        "PLANTGUARD_ENVIRONMENT",
        "PLANTGUARD_LOG_FORMAT",
        "PLANTGUARD_LOG_LEVEL",
    }
)


def _default_config_path() -> Path:
    """Prefer an operator-visible local configuration, then use the packaged fallback."""
    if LOCAL_DEFAULT_CONFIG_PATH.is_file():
        return LOCAL_DEFAULT_CONFIG_PATH
    return PACKAGED_DEFAULT_CONFIG_PATH


def _validate_environment_variable_names() -> None:
    """Reject misspelled PlantGuard overrides instead of silently using a default."""
    unknown_variables = sorted(
        variable_name
        for variable_name in os.environ
        if variable_name.upper().startswith("PLANTGUARD_")
        and variable_name.upper() not in ALLOWED_ENVIRONMENT_VARIABLES
    )
    if unknown_variables:
        raise ConfigurationError(
            "Application configuration could not be loaded.",
            context={
                "reason": "unknown_environment_variable",
                "variables": unknown_variables,
            },
        )


class Environment(StrEnum):
    """Supported application deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Supported application logging thresholds."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(StrEnum):
    """Supported human-readable and machine-readable log formats."""

    CONSOLE = "console"
    JSON = "json"


class ApiSettings(BaseModel):
    """Network settings for the local HTTP API."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8000, ge=1, le=65535)


class DatabaseSettings(BaseModel):
    """Connection settings for the application's authoritative structured storage."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    url: SecretStr = SecretStr("sqlite+aiosqlite:///./data/plantguard-uav.sqlite3")
    connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)


class Settings(BaseSettings):
    """Complete validated settings used by one application process."""

    model_config = SettingsConfigDict(
        env_prefix="PLANTGUARD_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=None,
        yaml_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )

    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat = LogFormat.CONSOLE
    api: ApiSettings = Field(default_factory=ApiSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define highest-to-lowest configuration source priority."""
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(
                settings_cls,
                yaml_file=_default_config_path(),
                yaml_file_encoding="utf-8",
            ),
            init_settings,
            file_secret_settings,
        )


class _ExplicitSettings(Settings):
    """Validate explicitly supplied values without consulting runtime sources."""

    model_config = SettingsConfigDict(
        env_file=None,
        yaml_file=None,
        yaml_file_encoding=None,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Use only caller-supplied values for deterministic dependency injection."""
        return (init_settings,)


def settings_from_values(values: Mapping[str, object]) -> Settings:
    """Validate explicit settings without reading environment or configuration files."""
    return _ExplicitSettings.model_validate(values)


def load_settings() -> Settings:
    """Load and validate configuration without exposing sensitive input values."""
    _validate_environment_variable_names()
    if not _default_config_path().is_file():
        raise ConfigurationError(
            "Application configuration could not be loaded.",
            context={"reason": "default_configuration_missing"},
        )

    try:
        return Settings()
    except (ValidationError, SettingsError, OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(
            "Application configuration could not be loaded.",
            context={"reason": "configuration_invalid"},
        ) from exc
