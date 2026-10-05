from __future__ import annotations

from fastapi import APIRouter

from backend.models.api import HealthResponse
from backend.services.health import health_status

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service and Elasticsearch connectivity",
    description=(
        "Report the service status and whether the configured Elasticsearch "
        "cluster is reachable. The endpoint answers 200 even when "
        "Elasticsearch is unavailable: orchestration health checks should "
        "read the ``elasticsearch`` field of the JSON body to distinguish a "
        "degraded service from a dead process."
    ),
)
def get_health() -> HealthResponse:
    return health_status()
