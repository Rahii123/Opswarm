"""
OpsSwarm — Test Suite: State Schema
======================================
Tests for state schema structure, initial state factory,
and TypedDict field contracts.
"""

import pytest
from core.constants import AgentName, IncidentStatus, RiskLevel, Severity
from core.state_schema import Alert, AgentDecision, RCAReport, create_initial_state


class TestAlert:
    def test_alert_auto_generates_ids(self):
        a = Alert(service="auth-service", message="Login failed")
        assert a.alert_id
        assert a.trace_id
        assert "Z" in a.timestamp

    def test_alert_to_dict_contains_required_fields(self):
        a = Alert(service="auth-service", severity="CRITICAL", event_type="brute_force")
        d = a.to_dict()
        for key in ["alert_id", "timestamp", "service", "severity", "event_type", "message"]:
            assert key in d


class TestCreateInitialState:
    def test_creates_valid_state(self):
        raw = [{"alert_id": "test-1", "message": "test alert"}]
        state = create_initial_state(raw_alerts=raw)
        assert state["schema_version"] == "1.0"
        assert state["alert_count"] == 1
        assert state["incident_status"] == IncidentStatus.DETECTED.value
        assert state["severity"] == Severity.MEDIUM.value
        assert state["risk_score"] == 0.0
        assert state["agent_decisions"] == []
        assert state["errors"] == []

    def test_incident_id_is_auto_generated(self):
        state = create_initial_state(raw_alerts=[])
        assert state["incident_id"].startswith("INC-")
        assert len(state["incident_id"]) == 12  # INC- + 8 chars

    def test_custom_correlation_id_is_respected(self):
        state = create_initial_state(raw_alerts=[], correlation_id="my-corr-id")
        assert state["correlation_id"] == "my-corr-id"

    def test_initial_risk_level_is_safe(self):
        state = create_initial_state(raw_alerts=[])
        assert state["risk_level"] == RiskLevel.SAFE.value

    def test_initial_agent_is_sentry(self):
        state = create_initial_state(raw_alerts=[])
        assert state["current_agent"] == AgentName.SENTRY.value


class TestAgentDecision:
    def test_decision_auto_generates_id(self):
        d = AgentDecision(agent_name="sentry", action="anomaly_detected")
        assert d.decision_id
        assert d.timestamp

    def test_decision_confidence_default(self):
        d = AgentDecision()
        assert d.confidence == 0.0


class TestRCAReport:
    def test_rca_report_structure(self):
        r = RCAReport(
            incident_id="INC-001",
            root_cause="Brute force attack",
            confidence=0.91,
        )
        assert r.report_id
        assert r.generated_by == AgentName.INVESTIGATOR.value
        assert r.contributing_factors == []
        assert r.recommendations == []
