"""
OpsSwarm — Incidents Router
==============================
REST endpoints for incident management.
All write operations emit audit log entries.
Phase 0: Stubs that return mock data — wired to DB in Phase 1.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

router = APIRouter()


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class AlertIngestRequest(BaseModel):
    """Payload sent to trigger a new incident pipeline."""
    service: str = Field(..., description="Name of the affected service")
    severity: str = Field(..., pattern="^(INFO|LOW|MEDIUM|HIGH|CRITICAL)$")
    event_type: str = Field(..., description="EventType enum value")
    message: str = Field(..., max_length=1000)
    host: str = Field(default="unknown")
    region: str = Field(default="us-east-1")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentSummary(BaseModel):
    incident_id: str
    title: str
    severity: str
    status: str
    affected_service: str
    detected_at: str
    risk_score: float | None = None


class IncidentDetail(IncidentSummary):
    description: str | None = None
    root_cause_summary: str | None = None
    confidence_score: float | None = None
    risk_level: str | None = None
    remediation_status: str | None = None
    agent_decisions_count: int = 0
    closed_at: str | None = None


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.post(
    "/incidents/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a new alert and trigger the pipeline",
)
async def ingest_alert(payload: AlertIngestRequest) -> dict[str, str]:
    """
    Accepts an incoming alert and queues it for the Sentry agent pipeline.
    Returns immediately with a correlation_id for tracking.

    Phase 0: Returns a mock response.
    Phase 1: Will enqueue to SQS and create a DB record.
    """
    import uuid
    correlation_id = str(uuid.uuid4())
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    return {
        "status": "accepted",
        "incident_id": incident_id,
        "correlation_id": correlation_id,
        "message": "Alert accepted. Pipeline will begin processing shortly.",
    }


@router.get(
    "/incidents",
    response_model=list[IncidentSummary],
    summary="List all incidents",
)
async def list_incidents(
    status: str | None = Query(None, description="Filter by incident status"),
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[IncidentSummary]:
    """
    Returns a paginated list of incidents.
    Phase 0: Returns mock data. Phase 1: Queries PostgreSQL.
    """
    mock = [
        IncidentSummary(
            incident_id="INC-A1B2C3D4",
            title="Brute force authentication attack on auth-service",
            severity="CRITICAL",
            status="INVESTIGATING",
            affected_service="auth-service",
            detected_at="2024-01-15T10:23:00Z",
            risk_score=8.5,
        ),
        IncidentSummary(
            incident_id="INC-E5F6A7B8",
            title="Database connection pool exhaustion on db-primary",
            severity="HIGH",
            status="REMEDIATING",
            affected_service="db-primary",
            detected_at="2024-01-15T09:47:00Z",
            risk_score=6.2,
        ),
    ]
    return mock


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentDetail,
    summary="Get incident details",
)
async def get_incident(
    incident_id: str = Path(..., description="Incident ID, e.g. INC-A1B2C3D4"),
) -> IncidentDetail:
    """
    Returns full details for a single incident including RCA summary.
    Phase 0: Returns mock data. Phase 1: Queries PostgreSQL + joins.
    """
    if incident_id == "INC-A1B2C3D4":
        return IncidentDetail(
            incident_id="INC-A1B2C3D4",
            title="Brute force authentication attack on auth-service",
            severity="CRITICAL",
            status="INVESTIGATING",
            affected_service="auth-service",
            detected_at="2024-01-15T10:23:00Z",
            description="Sustained brute force attack detected. 847 failed logins in 3 minutes from 12 distinct IPs.",
            root_cause_summary="Coordinated credential stuffing attack targeting the /api/v1/auth/login endpoint.",
            confidence_score=0.91,
            risk_score=8.5,
            risk_level="HIGH",
            remediation_status="AWAITING_APPROVAL",
            agent_decisions_count=4,
        )
    raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")


@router.patch(
    "/incidents/{incident_id}/approve",
    summary="Approve a pending human-in-the-loop remediation",
)
async def approve_remediation(
    incident_id: str = Path(..., description="Incident ID"),
    approver: str = Query(..., description="Approver identifier (email or user ID)"),
) -> dict[str, str]:
    """
    Human approval endpoint for high-risk remediation actions.
    Phase 0: Mock response. Phase 1: Updates DB + triggers Remediator.
    """
    return {
        "status": "approved",
        "incident_id": incident_id,
        "approved_by": approver,
        "approved_at": datetime.utcnow().isoformat() + "Z",
        "message": "Remediation approved. Remediator agent will execute shortly.",
    }
