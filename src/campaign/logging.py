"""Structlog setup with redaction for outreach-sensitive fields."""
from __future__ import annotations

import logging
import sys

import structlog

from campaign.config import get_settings

# Research/outreach payloads never logged verbatim. IDs and structural fields
# pass through unchanged.
_REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "decision_maker",
        "milestone",
        "email_body",
        "subject",
        "lead_analysis",
        "generated_email",
        "critique",
        "prospect_email",
    }
)


def _redact_sensitive(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    for key in list(event_dict.keys()):
        if key in _REDACTED_KEYS:
            val = event_dict[key]
            if isinstance(val, str) and len(val) > 12:
                event_dict[key] = f"{val[:12]}…<redacted {len(val) - 12} chars>"
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        _redact_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
