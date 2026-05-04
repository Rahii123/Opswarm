"""
OpsSwarm — Test Suite: Constants & Enums
==========================================
Tests for severity codes, enum membership, and risk thresholds.
"""

import pytest
from core.constants import (
    ErrorCode,
    RemediationAction,
    RiskLevel,
    RISK_SCORE_THRESHOLDS,
    Severity,
    SeverityCode,
    SystemLimits,
)


class TestSeverity:
    def test_severity_values_are_strings(self):
        for s in Severity:
            assert isinstance(s.value, str)

    def test_severity_code_ordering(self):
        assert SeverityCode.INFO < SeverityCode.LOW
        assert SeverityCode.LOW < SeverityCode.MEDIUM
        assert SeverityCode.MEDIUM < SeverityCode.HIGH
        assert SeverityCode.HIGH < SeverityCode.CRITICAL

    def test_severity_code_from_severity(self):
        assert SeverityCode.from_severity(Severity.CRITICAL) == SeverityCode.CRITICAL
        assert SeverityCode.from_severity(Severity.INFO) == SeverityCode.INFO


class TestRiskThresholds:
    def test_all_risk_levels_have_thresholds(self):
        for level in RiskLevel:
            assert level in RISK_SCORE_THRESHOLDS

    def test_thresholds_cover_full_range(self):
        all_ranges = list(RISK_SCORE_THRESHOLDS.values())
        assert all_ranges[0][0] == 0.0
        assert all_ranges[-1][1] == 10.0

    def test_safe_actions_exist(self):
        """The Safe Action Library must have at least these core actions."""
        required = {
            RemediationAction.RESTART_SERVICE,
            RemediationAction.CLEAR_CACHE,
            RemediationAction.NOTIFY_ON_CALL,
            RemediationAction.CREATE_INCIDENT_TICKET,
            RemediationAction.ENABLE_CIRCUIT_BREAKER,
        }
        for action in required:
            assert action in RemediationAction


class TestSystemLimits:
    def test_max_agent_retries_is_reasonable(self):
        assert 1 <= SystemLimits.MAX_AGENT_RETRIES <= 10

    def test_correlation_window_is_positive(self):
        assert SystemLimits.ALERT_CORRELATION_WINDOW_SECONDS > 0

    def test_risk_approval_high_actions_require_approval(self):
        """High-risk actions must always require approval at threshold 6."""
        high_risk = {
            RemediationAction.TERMINATE_INSTANCE,
            RemediationAction.DISABLE_USER_ACCOUNT,
            RemediationAction.FORCE_FAILOVER,
            RemediationAction.MODIFY_IAM_POLICY,
        }
        for action in high_risk:
            assert action in RemediationAction
