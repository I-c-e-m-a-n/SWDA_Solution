"""Metadata-only JSON events. Never pass exception messages or request data here."""

import json
import logging

from . import AGENT_VERSION, CATALOGUE_VERSION, PUBLIC_TOOL

logger = logging.getLogger("swda.audit")


def event(
    trace_id: str,
    status: str,
    duration_ms: float,
    revision: int | None = None,
    operation: str = "tools/call",
):
    logger.info(
        json.dumps(
            {
                "trace_id": trace_id,
                "agent_version": AGENT_VERSION,
                "policy_revision": revision,
                "tool": PUBLIC_TOOL,
                "operation": operation,
                "status": status,
                "catalogue_version": CATALOGUE_VERSION,
                "duration_ms": round(duration_ms, 3),
            },
            sort_keys=True,
        )
    )
