"""Structured logging shared by application and standard-library loggers."""

from collections.abc import Mapping
import logging
import sys
from typing import cast

import structlog
from structlog.stdlib import BoundLogger, ProcessorFormatter
from structlog.typing import EventDict, Processor, WrappedLogger

from plantguard_uav.config import LogFormat, LogLevel

REDACTED_VALUE = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "cookie",
        "database_url",
        "dsn",
        "passwd",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)
LOG_LEVEL_VALUES: dict[LogLevel, int] = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
}


def _normalise_key(key: object) -> str:
    """Normalise a structured field name before checking if it is sensitive."""
    return str(key).strip().lower().replace("-", "_")


def _is_sensitive_key(key: object) -> bool:
    """Recognise exact secret fields and namespaced variants such as client_secret."""
    normalised_key = _normalise_key(key)
    return normalised_key in SENSITIVE_KEYS or any(
        normalised_key.endswith(f"_{sensitive_key}") for sensitive_key in SENSITIVE_KEYS
    )


def _redact_value(key: object, value: object) -> object:
    """Recursively replace values stored below sensitive structured keys."""
    if _is_sensitive_key(key):
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return {
            nested_key: _redact_value(nested_key, nested_value)
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_value("", item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value("", item) for item in value)
    return value


def redact_sensitive_values(
    _logger: WrappedLogger,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Remove secrets from structured log fields before rendering the event."""
    for key, value in tuple(event_dict.items()):
        event_dict[key] = _redact_value(key, value)
    return event_dict


def _shared_processors() -> list[Processor]:
    """Build processors used by both Structlog and standard-library records."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        redact_sensitive_values,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]


def configure_logging(log_level: LogLevel, log_format: LogFormat) -> None:
    """Configure one repeatable logging pipeline for every application logger."""
    shared_processors = _shared_processors()
    renderer: Processor
    if log_format is LogFormat.JSON:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    formatter = ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    numeric_level = LOG_LEVEL_VALUES[log_level]
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(numeric_level)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=BoundLogger,
        cache_logger_on_first_use=False,
    )


def get_logger(component: str) -> BoundLogger:
    """Return a named structured logger with its component bound to every event."""
    logger = structlog.get_logger(component).bind(component=component)
    return cast(BoundLogger, logger)
