"""
OpsSwarm — Custom Exception Hierarchy
======================================
All application exceptions derive from OpsSwarmError.
This allows callers to catch the base class or specific subtypes.

Usage:
    from core.exceptions import IncidentNotFoundError, AgentExecutionError
    raise IncidentNotFoundError(incident_id="INC-001")
"""

from typing import Any


# ─── BASE ─────────────────────────────────────────────────────────────────────

class OpsSwarmError(Exception):
    """Base exception for all OpsSwarm errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"details={self.details!r})"
        )


# ─── CONFIGURATION ────────────────────────────────────────────────────────────

class ConfigurationError(OpsSwarmError):
    """Raised when application configuration is invalid or missing."""


class MissingEnvironmentVariableError(ConfigurationError):
    """Raised when a required environment variable is not set."""

    def __init__(self, variable_name: str) -> None:
        super().__init__(
            message=f"Required environment variable '{variable_name}' is not set.",
            error_code="ERR_CONFIG_001",
            details={"variable": variable_name},
        )


# ─── DATABASE ─────────────────────────────────────────────────────────────────

class DatabaseError(OpsSwarmError):
    """Base class for database-related errors."""


class ConnectionPoolExhaustedError(DatabaseError):
    """Raised when the database connection pool is exhausted."""

    def __init__(self, pool_size: int) -> None:
        super().__init__(
            message=f"Database connection pool exhausted (max_size={pool_size}).",
            error_code="ERR_DB_001",
            details={"pool_size": pool_size},
        )


class RecordNotFoundError(DatabaseError):
    """Raised when a requested database record does not exist."""

    def __init__(self, model: str, identifier: Any) -> None:
        super().__init__(
            message=f"{model} with identifier '{identifier}' not found.",
            error_code="ERR_DB_404",
            details={"model": model, "identifier": str(identifier)},
        )


# ─── INCIDENT ─────────────────────────────────────────────────────────────────

class IncidentError(OpsSwarmError):
    """Base class for incident-related errors."""


class IncidentNotFoundError(IncidentError):
    """Raised when an incident cannot be found."""

    def __init__(self, incident_id: str) -> None:
        super().__init__(
            message=f"Incident '{incident_id}' not found.",
            error_code="ERR_INC_404",
            details={"incident_id": incident_id},
        )


class IncidentAlreadyClosedError(IncidentError):
    """Raised when attempting to modify a closed incident."""

    def __init__(self, incident_id: str) -> None:
        super().__init__(
            message=f"Incident '{incident_id}' is already closed and cannot be modified.",
            error_code="ERR_INC_409",
            details={"incident_id": incident_id},
        )


class DuplicateIncidentError(IncidentError):
    """Raised when a duplicate incident is detected during correlation."""

    def __init__(self, incident_id: str, duplicate_of: str) -> None:
        super().__init__(
            message=f"Incident '{incident_id}' is a duplicate of '{duplicate_of}'.",
            error_code="ERR_INC_DUP",
            details={"incident_id": incident_id, "duplicate_of": duplicate_of},
        )


# ─── AGENT ────────────────────────────────────────────────────────────────────

class AgentError(OpsSwarmError):
    """Base class for agent execution errors."""


class AgentExecutionError(AgentError):
    """Raised when an agent fails during execution."""

    def __init__(self, agent_name: str, reason: str) -> None:
        super().__init__(
            message=f"Agent '{agent_name}' failed: {reason}",
            error_code="ERR_AGENT_001",
            details={"agent_name": agent_name, "reason": reason},
        )


class AgentTimeoutError(AgentError):
    """Raised when an agent exceeds its execution time limit."""

    def __init__(self, agent_name: str, timeout_seconds: int) -> None:
        super().__init__(
            message=f"Agent '{agent_name}' timed out after {timeout_seconds}s.",
            error_code="ERR_AGENT_TIMEOUT",
            details={"agent_name": agent_name, "timeout_seconds": timeout_seconds},
        )


class MaxRetriesExceededError(AgentError):
    """Raised when an agent exceeds its maximum retry count."""

    def __init__(self, agent_name: str, max_retries: int) -> None:
        super().__init__(
            message=f"Agent '{agent_name}' exceeded max retries ({max_retries}).",
            error_code="ERR_AGENT_RETRY",
            details={"agent_name": agent_name, "max_retries": max_retries},
        )


# ─── LLM ──────────────────────────────────────────────────────────────────────

class LLMError(OpsSwarmError):
    """Base class for LLM provider errors."""


class LLMRateLimitError(LLMError):
    """Raised when the LLM provider returns a rate limit error."""

    def __init__(self, provider: str, retry_after: int | None = None) -> None:
        super().__init__(
            message=f"LLM provider '{provider}' rate limit exceeded.",
            error_code="ERR_LLM_429",
            details={"provider": provider, "retry_after_seconds": retry_after},
        )


class LLMResponseParseError(LLMError):
    """Raised when the LLM response cannot be parsed into the expected schema."""

    def __init__(self, agent_name: str, raw_response: str) -> None:
        super().__init__(
            message=f"Agent '{agent_name}' could not parse LLM response.",
            error_code="ERR_LLM_PARSE",
            details={"agent_name": agent_name, "raw_response": raw_response[:200]},
        )


# ─── REMEDIATION ──────────────────────────────────────────────────────────────

class RemediationError(OpsSwarmError):
    """Base class for remediation errors."""


class UnsafeActionError(RemediationError):
    """Raised when an action is not in the Safe Action Library."""

    def __init__(self, action: str) -> None:
        super().__init__(
            message=f"Action '{action}' is not in the Safe Action Library and cannot be auto-executed.",
            error_code="ERR_REM_UNSAFE",
            details={"action": action},
        )


class ApprovalRequiredError(RemediationError):
    """Raised when a high-risk action requires human approval."""

    def __init__(self, action: str, risk_score: float) -> None:
        super().__init__(
            message=f"Action '{action}' requires human approval (risk_score={risk_score}).",
            error_code="ERR_REM_APPROVAL",
            details={"action": action, "risk_score": risk_score},
        )


class ApprovalTimeoutError(RemediationError):
    """Raised when human approval is not received within the timeout window."""

    def __init__(self, incident_id: str, timeout_seconds: int) -> None:
        super().__init__(
            message=f"Approval for incident '{incident_id}' timed out after {timeout_seconds}s.",
            error_code="ERR_REM_TIMEOUT",
            details={"incident_id": incident_id, "timeout_seconds": timeout_seconds},
        )


# ─── VECTOR STORE ─────────────────────────────────────────────────────────────

class VectorStoreError(OpsSwarmError):
    """Base class for Qdrant/vector store errors."""


class CollectionNotFoundError(VectorStoreError):
    """Raised when a Qdrant collection does not exist."""

    def __init__(self, collection_name: str) -> None:
        super().__init__(
            message=f"Qdrant collection '{collection_name}' does not exist.",
            error_code="ERR_VEC_404",
            details={"collection_name": collection_name},
        )


# ─── VALIDATION ───────────────────────────────────────────────────────────────

class ValidationError(OpsSwarmError):
    """Raised when input data fails schema validation."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(
            message=f"Validation failed for field '{field}': {reason}",
            error_code="ERR_VAL_001",
            details={"field": field, "reason": reason},
        )
