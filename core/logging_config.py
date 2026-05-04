"""
OpsSwarm — Structured Logging Configuration
============================================
Sets up structlog with JSON output for production and
colourised console output for development.

Every log entry automatically includes:
  - timestamp (ISO-8601 UTC)
  - log level
  - logger name
  - correlation_id (if set in context)
  - service name
  - environment

Usage:
    from core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("incident_detected", incident_id="INC-001", severity="CRITICAL")
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from core.config import settings


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject application-level context into every log entry."""
    event_dict["app"] = settings.app_name
    event_dict["env"] = settings.app_env
    event_dict["version"] = settings.app_version
    return event_dict


def drop_colour_message_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Remove the internal colour_message key added by rich."""
    event_dict.pop("colour_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.
    Call once at application startup (in api/main.py or scripts).
    """
    log_level = getattr(logging, settings.app_log_level, logging.INFO)

    # Shared processors applied to every log entry
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,         # Picks up bind_contextvars()
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        add_app_context,
        drop_colour_message_key,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production or not settings.app_debug:
        # Production: structured JSON output
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: human-friendly colourised console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Apply to root logger so all stdlib loggers (uvicorn, sqlalchemy, etc.) go through structlog
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers in production
    for noisy_logger in ["uvicorn.access", "botocore", "boto3", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a named structlog logger.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A bound structlog logger ready to use.
    """
    return structlog.get_logger(name)


def bind_request_context(
    correlation_id: str,
    request_id: str | None = None,
    agent_name: str | None = None,
    incident_id: str | None = None,
) -> None:
    """
    Bind context variables to the current async context.
    These will appear on every log entry made from this context.

    Call at the start of each request or agent execution.
    Clear with clear_request_context() when done.
    """
    ctx: dict[str, str] = {"correlation_id": correlation_id}
    if request_id:
        ctx["request_id"] = request_id
    if agent_name:
        ctx["agent"] = agent_name
    if incident_id:
        ctx["incident_id"] = incident_id
    structlog.contextvars.bind_contextvars(**ctx)


def clear_request_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
