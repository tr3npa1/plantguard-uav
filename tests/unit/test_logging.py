import json
import logging

import pytest

from plantguard_uav.config import LogFormat, LogLevel
from plantguard_uav.logging import REDACTED_VALUE, configure_logging, get_logger


def _single_output_line(capsys: pytest.CaptureFixture[str]) -> str:
    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert len(lines) == 1
    return lines[0]


def test_repeated_configuration_does_not_duplicate_events(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(LogLevel.INFO, LogFormat.JSON)
    configure_logging(LogLevel.INFO, LogFormat.JSON)

    get_logger("test.logging").info("one_event")

    payload = json.loads(_single_output_line(capsys))
    assert payload["event"] == "one_event"


def test_json_logs_include_context_and_recursively_redact_secrets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(LogLevel.INFO, LogFormat.JSON)

    get_logger("test.logging").info(
        "credentials_received",
        password="top-secret-password",
        safe_value="visible",
        nested={"api_key": "top-secret-key", "items": [{"token": "top-secret-token"}]},
        tuple_values=({"database-url": "top-secret-dsn"},),
        variants={
            "auth_token": "top-secret-auth-token",
            "client_secret": "top-secret-client-secret",
            "proxy-authorization": "top-secret-proxy-auth",
            "set-cookie": "top-secret-cookie",
            "user_password": "top-secret-user-password",
            "x-api-key": "top-secret-api-key",
            "token_count": 3,
        },
    )

    rendered = _single_output_line(capsys)
    payload = json.loads(rendered)
    assert "top-secret" not in rendered
    assert payload["password"] == REDACTED_VALUE
    assert payload["nested"]["api_key"] == REDACTED_VALUE
    assert payload["nested"]["items"][0]["token"] == REDACTED_VALUE
    assert payload["tuple_values"][0]["database-url"] == REDACTED_VALUE
    assert payload["variants"]["auth_token"] == REDACTED_VALUE
    assert payload["variants"]["client_secret"] == REDACTED_VALUE
    assert payload["variants"]["proxy-authorization"] == REDACTED_VALUE
    assert payload["variants"]["set-cookie"] == REDACTED_VALUE
    assert payload["variants"]["user_password"] == REDACTED_VALUE
    assert payload["variants"]["x-api-key"] == REDACTED_VALUE
    assert payload["variants"]["token_count"] == 3
    assert payload["safe_value"] == "visible"
    assert payload["component"] == "test.logging"
    assert payload["level"] == "info"
    assert payload["timestamp"].endswith("Z")


def test_standard_library_logs_use_the_same_json_and_redaction(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(LogLevel.INFO, LogFormat.JSON)

    logging.getLogger("external.component").info(
        "stdlib_event",
        extra={"authorization": "Bearer top-secret", "details": {"dsn": "top-secret-dsn"}},
    )

    rendered = _single_output_line(capsys)
    payload = json.loads(rendered)
    assert "top-secret" not in rendered
    assert payload["event"] == "stdlib_event"
    assert payload["authorization"] == REDACTED_VALUE
    assert payload["details"]["dsn"] == REDACTED_VALUE
    assert payload["logger"] == "external.component"


def test_console_format_is_readable_and_log_level_filters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(LogLevel.WARNING, LogFormat.CONSOLE)
    logger = get_logger("test.console")

    logger.info("hidden_event")
    logger.warning("visible_event", safe_value="shown")

    rendered = _single_output_line(capsys)
    assert "hidden_event" not in rendered
    assert "visible_event" in rendered
    assert "safe_value=shown" in rendered
