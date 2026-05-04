"""
OpsSwarm — Health Check Router
================================
Simple health and readiness endpoints.
Used by load balancers, Docker, and Kubernetes probes.
"""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health_check() -> HealthResponse:
    """
    Returns 200 if the application process is alive.
    Used as a liveness probe by Docker and Kubernetes.
    """
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness_check() -> ReadinessResponse:
    """
    Returns 200 if the application is ready to serve traffic.
    Checks downstream dependencies (DB, Redis, Qdrant).
    Currently returns degraded checks — will be wired up in Phase 1.
    """
    checks: dict[str, str] = {
        "api": "ok",
        "database": "pending",  # Wire up in Phase 1
        "redis": "pending",
        "qdrant": "pending",
    }
    overall = "ok" if all(v in ("ok", "pending") for v in checks.values()) else "degraded"
    return ReadinessResponse(status=overall, checks=checks)
