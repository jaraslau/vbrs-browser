"""Health-check business logic for the vbrs-browser API.

The health endpoint intentionally stays available while Elasticsearch is
down: it probes connectivity, translates the binary ping result into the
machine-readable report consumed by the API, and lets orchestration health
checks decide what to do with it.
"""

from __future__ import annotations

import logging

from backend.elasticsearch.client import ping_elasticsearch
from backend.models.api import HealthResponse

logger = logging.getLogger(__name__)


def health_status() -> HealthResponse:
    try:
        connected = ping_elasticsearch()
    except Exception:
        logger.exception("Elasticsearch connectivity probe failed")
        connected = False

    return HealthResponse(
        status="ok",
        elasticsearch="connected" if connected else "unavailable",
    )
