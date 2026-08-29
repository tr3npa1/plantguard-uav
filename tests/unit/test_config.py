from pathlib import Path

from pydantic import SecretStr, ValidationError
import pytest

import plantguard_uav.config as config_module
from plantguard_uav.config import (
    ApiSettings,
    DatabaseSettings,
    Environment,
    LogFormat,
    LogLevel,
    Settings,
    load_settings,
    settings_from_values,
)
from plantguard_uav.errors import ConfigurationError, PersistenceError

VALID_CONFIG = """environment: development
log_level: INFO
log_format: console
api:
  host: "127.0.0.1"
  port: 7000
database:
  url: "sqlite+aiosqlite:///./data/test.sqlite3"
  connect_timeout_seconds: 5
"""


def _write_default_config(root: Path, content: str = VALID_CONFIG) -> None:
    config_directory = root / "configs"
    config_directory.mkdir()
    (config_directory / "default.yaml").write_text(content, encoding="utf-8")


def test_yaml_configuration_loads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write_default_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.environment.value == "development"
    assert settings.log_level is LogLevel.INFO
    assert settings.log_format is LogFormat.CONSOLE
    assert settings.api == ApiSettings(host="127.0.0.1", port=7000)
    assert settings.database.url.get_secret_value().endswith("/data/test.sqlite3")
    assert settings.database.connect_timeout_seconds == 5.0


def test_environment_beats_dotenv_and_yaml(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    (tmp_path / ".env").write_text("PLANTGUARD_API__PORT=7100\n", encoding="utf-8")
    monkeypatch.setenv("PLANTGUARD_API__PORT", "7200")
    monkeypatch.chdir(tmp_path)

    assert load_settings().api.port == 7200


def test_dotenv_beats_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write_default_config(tmp_path)
    (tmp_path / ".env").write_text("PLANTGUARD_API__PORT=7100\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert load_settings().api.port == 7100


def test_nested_environment_variable_overrides_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    monkeypatch.setenv("PLANTGUARD_API__HOST", "0.0.0.0")
    monkeypatch.chdir(tmp_path)

    assert load_settings().api.host == "0.0.0.0"


def test_nested_environment_variables_override_database_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    override_url = "sqlite+aiosqlite:///./data/environment.sqlite3"
    monkeypatch.setenv("PLANTGUARD_DATABASE__URL", override_url)
    monkeypatch.setenv("PLANTGUARD_DATABASE__CONNECT_TIMEOUT_SECONDS", "2.5")
    monkeypatch.chdir(tmp_path)

    database = load_settings().database

    assert database.url.get_secret_value() == override_url
    assert database.connect_timeout_seconds == 2.5


def test_database_container_environment_variable_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    monkeypatch.setenv(
        "PLANTGUARD_DATABASE",
        '{"url":"sqlite+aiosqlite:///./data/container.sqlite3","connect_timeout_seconds":3}',
    )
    monkeypatch.chdir(tmp_path)

    database = load_settings().database

    assert database.url.get_secret_value().endswith("/data/container.sqlite3")
    assert database.connect_timeout_seconds == 3.0


def test_yaml_beats_constructor_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write_default_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    settings = Settings(api=ApiSettings(port=7300))

    assert settings.api.port == 7000


def test_code_defaults_fill_missing_yaml_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path, "environment: testing\n")
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.log_level is LogLevel.INFO
    assert settings.api.port == 8000


def test_explicit_values_are_validated_without_runtime_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    monkeypatch.setenv("PLANTGUARD_ENVIRONMENT", "development")
    monkeypatch.chdir(tmp_path)

    settings = settings_from_values(
        {
            "environment": "production",
            "log_format": "json",
            "api": {"host": "0.0.0.0", "port": 9000},
        }
    )

    assert settings.environment is Environment.PRODUCTION
    assert settings.log_format is LogFormat.JSON
    assert settings.api.port == 9000
    assert settings.database == DatabaseSettings()


def test_packaged_yaml_is_used_outside_the_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.api.port == 8000


def test_repository_and_packaged_defaults_match(project_root: Path) -> None:
    repository_default = project_root / "configs" / "default.yaml"

    assert (
        repository_default.read_bytes() == config_module.PACKAGED_DEFAULT_CONFIG_PATH.read_bytes()
    )


def test_unknown_prefixed_environment_variable_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    monkeypatch.setenv("PLANTGUARD_TYP0", "private-value")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError, match="could not be loaded") as error:
        load_settings()

    assert error.value.context == {
        "reason": "unknown_environment_variable",
        "variables": ["PLANTGUARD_TYP0"],
    }
    assert "private-value" not in error.value.public_message


@pytest.mark.parametrize("port", ["0", "65536"])
def test_invalid_port_is_rejected(
    port: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    monkeypatch.setenv("PLANTGUARD_API__PORT", port)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError, match="could not be loaded"):
        load_settings()


@pytest.mark.parametrize("timeout", ["0", "-0.1", "60.1"])
def test_invalid_database_timeout_is_rejected(
    timeout: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path)
    monkeypatch.setenv("PLANTGUARD_DATABASE__CONNECT_TIMEOUT_SECONDS", timeout)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError, match="could not be loaded"):
        load_settings()


def test_database_settings_are_frozen() -> None:
    database = DatabaseSettings()

    with pytest.raises(ValidationError):
        database.__setattr__("connect_timeout_seconds", 10)


def test_database_url_is_redacted_from_representations() -> None:
    private_url = "postgresql+asyncpg://private-user:private-password@database/plantguard"
    database = DatabaseSettings(url=SecretStr(private_url))

    assert private_url not in repr(database)
    assert private_url not in database.model_dump_json()
    assert "**********" in repr(database)


def test_unknown_yaml_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path, f"{VALID_CONFIG}unknown_setting: true\n")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError, match="could not be loaded"):
        load_settings()


def test_malformed_yaml_is_wrapped_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_default_config(tmp_path, "api: [unterminated\n")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError, match="could not be loaded") as error:
        load_settings()

    assert "unterminated" not in error.value.public_message
    assert error.value.context == {"reason": "configuration_invalid"}


def test_missing_yaml_is_reported_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        config_module,
        "PACKAGED_DEFAULT_CONFIG_PATH",
        tmp_path / "missing-packaged-default.yaml",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError, match="could not be loaded") as error:
        load_settings()

    assert error.value.context == {"reason": "default_configuration_missing"}


def test_persistence_error_uses_stable_safe_public_details() -> None:
    private_url = "postgresql+asyncpg://private-user:private-password@database/plantguard"
    error = PersistenceError(context={"reason": "connection_failed", "exception": private_url})

    assert error.error_code == "persistence_error"
    assert error.status_code == 500
    assert error.public_message == "Persistent storage operation could not be completed."
    assert private_url not in str(error)
    assert error.context["reason"] == "connection_failed"
