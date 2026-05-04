"""
OpsSwarm — LangGraph State Schema
===================================
Defines the TypedDict state that flows through the entire
multi-agent graph. Every agent reads from and writes to this
shared state object.

Design principles:
  - All fields are Optional so agents can run independently
  - Immutable history lists (never mutate, always append)
  - Strongly typed using Python TypedDict + dataclasses
  - Schema versioned for forward compatibility

Usage:
    from core.state_schema import OpsSwarmState, AgentDecision, Alert
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from typing_extensions import TypedDict

from core.constants import (
    AgentName,
    AgentStatus,
    ErrorCode,
    EventType,
    IncidentStatus,
    RiskLevel,
    Severity,
    ServiceName,
)


# ─── SUPPORTING DATA STRUCTURES ──────────────────────────────────────────────

@dataclass
class Alert:
    """A single alert event entering the system."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    service: str = ""
    severity: str = Severity.MEDIUM.value
    event_type: str = ""
    message: str = ""
    error_code: str | None = None
    host: str = ""
    region: str = "us-east-1"
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_log: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "service": self.service,
            "severity": self.severity,
            "event_type": self.event_type,
            "message": self.message,
            "error_code": self.error_code,
            "host": self.host,
            "region": self.region,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }


@dataclass
class AgentDecision:
    """Records a single decision made by an agent."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    action: str = ""
    rationale: str = ""
    confidence: float = 0.0       # 0.0 - 1.0
    risk_score: float | None = None  # 0.0 - 10.0
    status: str = AgentStatus.COMPLETED.value
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemediationStep:
    """A single step in the remediation plan."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    description: str = ""
    risk_level: str = RiskLevel.SAFE.value
    requires_approval: bool = False
    approved_by: str | None = None
    executed: bool = False
    result: str | None = None
    rollback_action: str | None = None
    timestamp: str | None = None


@dataclass
class RCAReport:
    """Root Cause Analysis report produced by the Investigator agent."""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    root_cause: str = ""
    contributing_factors: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    similar_incidents: list[str] = field(default_factory=list)
    generated_by: str = AgentName.INVESTIGATOR.value
    model_used: str = ""


# ─── MAIN GRAPH STATE ─────────────────────────────────────────────────────────

class OpsSwarmState(TypedDict, total=False):
    """
    The shared state object that flows through the LangGraph agent pipeline.

    Convention:
      - Sentry writes: incident_id, raw_alerts, severity, detected_at
      - Correlator writes: correlated_alerts, is_duplicate, suppressed
      - Context Builder writes: enriched_context, related_runbooks
      - Investigator writes: rca_report
      - Decision Router writes: risk_score, risk_level, requires_approval
      - Remediator writes: remediation_plan, remediation_results
      - Commander writes: final_report, postmortem
      - All agents append to: agent_decisions, errors
    """

    # ── Schema Metadata ───────────────────────────────────────
    schema_version: str                     # e.g. "1.0" — for forward compat

    # ── Correlation & Tracing ─────────────────────────────────
    correlation_id: str                     # Unique ID for this entire workflow run
    incident_id: str                        # e.g. "INC-2024-001"

    # ── Raw Input (Sentry Agent) ──────────────────────────────
    raw_alerts: list[dict[str, Any]]        # List of Alert.to_dict()
    detected_at: str                        # ISO-8601 timestamp
    severity: str                           # Severity enum value
    event_type: str                         # EventType enum value
    error_code: str | None                  # ErrorCode enum value
    affected_service: str                   # ServiceName enum value
    affected_host: str
    affected_region: str

    # ── Alert Correlation (Correlator Agent) ──────────────────
    correlated_alerts: list[dict[str, Any]] # Grouped related alerts
    alert_count: int                        # Number of alerts in group
    is_duplicate: bool                      # Is this a duplicate of existing incident?
    duplicate_of_incident_id: str | None
    suppressed: bool                        # Was this alert suppressed?
    suppression_reason: str | None

    # ── Enriched Context (Context Builder Agent) ───────────────
    enriched_context: dict[str, Any]        # Service topology, owners, SLAs
    related_runbooks: list[dict[str, Any]]  # Retrieved from Qdrant
    historical_similar_incidents: list[dict[str, Any]]
    service_owner: str | None
    sla_breach_risk: bool
    business_impact: str | None             # Human-readable impact statement

    # ── Root Cause Analysis (Investigator Agent) ───────────────
    rca_report: dict[str, Any]             # RCAReport.to_dict() equivalent
    root_cause_summary: str
    confidence_score: float                 # 0.0 - 1.0

    # ── Risk Assessment (Decision Router) ─────────────────────
    risk_score: float                       # 0.0 - 10.0
    risk_level: str                         # RiskLevel enum value
    requires_human_approval: bool
    risk_factors: list[str]
    approval_request_id: str | None
    approved_by: str | None
    approval_timestamp: str | None

    # ── Remediation (Remediator Agent) ────────────────────────
    remediation_plan: list[dict[str, Any]] # List of RemediationStep dicts
    remediation_results: list[dict[str, Any]]
    auto_actions_taken: int
    remediation_successful: bool | None

    # ── Final Report (Commander Agent) ────────────────────────
    incident_status: str                    # IncidentStatus enum value
    final_report: dict[str, Any]           # Complete structured report
    postmortem: str | None                 # Markdown postmortem document
    closed_at: str | None

    # ── Audit Trail (All Agents) ──────────────────────────────
    agent_decisions: list[dict[str, Any]]  # List of AgentDecision dicts
    errors: list[dict[str, Any]]           # Non-fatal errors encountered
    warnings: list[str]

    # ── Pipeline Control ──────────────────────────────────────
    current_agent: str                     # AgentName of currently executing agent
    next_agent: str | None                 # Override next routing decision
    pipeline_started_at: str
    pipeline_completed_at: str | None
    total_duration_ms: int | None


def create_initial_state(
    raw_alerts: list[dict[str, Any]],
    correlation_id: str | None = None,
    incident_id: str | None = None,
) -> OpsSwarmState:
    """
    Factory function to create a valid initial state for a new pipeline run.

    Args:
        raw_alerts: List of alert dicts from the Sentry agent.
        correlation_id: Optional override — auto-generated if not provided.
        incident_id: Optional override — auto-generated if not provided.

    Returns:
        A fully initialised OpsSwarmState ready for graph execution.
    """
    now = datetime.utcnow().isoformat() + "Z"
    return OpsSwarmState(
        schema_version="1.0",
        correlation_id=correlation_id or str(uuid.uuid4()),
        incident_id=incident_id or f"INC-{uuid.uuid4().hex[:8].upper()}",
        raw_alerts=raw_alerts,
        detected_at=now,
        severity=Severity.MEDIUM.value,
        event_type="",
        error_code=None,
        affected_service="",
        affected_host="",
        affected_region="us-east-1",
        correlated_alerts=[],
        alert_count=len(raw_alerts),
        is_duplicate=False,
        duplicate_of_incident_id=None,
        suppressed=False,
        suppression_reason=None,
        enriched_context={},
        related_runbooks=[],
        historical_similar_incidents=[],
        service_owner=None,
        sla_breach_risk=False,
        business_impact=None,
        rca_report={},
        root_cause_summary="",
        confidence_score=0.0,
        risk_score=0.0,
        risk_level=RiskLevel.SAFE.value,
        requires_human_approval=False,
        risk_factors=[],
        approval_request_id=None,
        approved_by=None,
        approval_timestamp=None,
        remediation_plan=[],
        remediation_results=[],
        auto_actions_taken=0,
        remediation_successful=None,
        incident_status=IncidentStatus.DETECTED.value,
        final_report={},
        postmortem=None,
        closed_at=None,
        agent_decisions=[],
        errors=[],
        warnings=[],
        current_agent=AgentName.SENTRY.value,
        next_agent=None,
        pipeline_started_at=now,
        pipeline_completed_at=None,
        total_duration_ms=None,
    )
