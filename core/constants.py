"""
OpsSwarm — System-Wide Constants & Enumerations
"""

from enum import Enum, IntEnum


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SeverityCode(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_severity(cls, severity: Severity) -> "SeverityCode":
        return cls[severity.value]


class IncidentStatus(str, Enum):
    DETECTED = "DETECTED"
    CORRELATING = "CORRELATING"
    ENRICHING = "ENRICHING"
    INVESTIGATING = "INVESTIGATING"
    ROUTING = "ROUTING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class AgentName(str, Enum):
    SENTRY = "sentry"
    CORRELATOR = "correlator"
    CONTEXT_BUILDER = "context_builder"
    INVESTIGATOR = "investigator"
    DECISION_ROUTER = "decision_router"
    REMEDIATOR = "remediator"
    COMMANDER = "commander"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    WAITING = "WAITING"
    SKIPPED = "SKIPPED"


class EventType(str, Enum):
    AUTH_LOGIN_FAILED = "authentication_failure"
    AUTH_TOKEN_ABUSE = "token_abuse"
    AUTH_BRUTE_FORCE = "brute_force_attack"
    DB_CONNECTION_ERROR = "db_connection_error"
    DB_POOL_EXHAUSTED = "db_pool_exhausted"
    DB_REPLICATION_LAG = "db_replication_lag"
    DB_SLOW_QUERY = "db_slow_query"
    API_5XX_SPIKE = "api_5xx_spike"
    API_LATENCY_HIGH = "api_latency_high"
    API_TIMEOUT = "api_timeout"
    INFRA_CPU_SPIKE = "cpu_spike"
    INFRA_MEMORY_LEAK = "memory_leak"
    INFRA_DISK_PRESSURE = "disk_pressure"
    INFRA_LAMBDA_THROTTLE = "lambda_throttle"
    PAYMENT_TIMEOUT = "payment_timeout"
    PAYMENT_CASCADE = "payment_cascade"
    SEC_PRIVILEGE_ESCALATION = "privilege_escalation"
    SEC_UNUSUAL_API_CALL = "unusual_api_call"
    DEPLOY_REGRESSION = "deployment_regression"
    DEPLOY_HEALTH_FAIL = "health_check_failure"


class ErrorCode(str, Enum):
    ERR_AUTH_001 = "ERR_AUTH_001"
    ERR_AUTH_002 = "ERR_AUTH_002"
    ERR_DB_001 = "ERR_DB_001"
    ERR_DB_002 = "ERR_DB_002"
    ERR_DB_003 = "ERR_DB_003"
    ERR_API_001 = "ERR_API_001"
    ERR_API_002 = "ERR_API_002"
    ERR_INFRA_001 = "ERR_INFRA_001"
    ERR_INFRA_002 = "ERR_INFRA_002"
    ERR_INFRA_003 = "ERR_INFRA_003"
    ERR_INFRA_004 = "ERR_INFRA_004"
    ERR_PAY_001 = "ERR_PAY_001"
    ERR_SEC_001 = "ERR_SEC_001"
    ERR_DEPLOY_001 = "ERR_DEPLOY_001"


class RemediationAction(str, Enum):
    """Safe Action Library — pre-approved operations."""
    # Low risk
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    SCALE_OUT = "scale_out"
    ROTATE_LOG = "rotate_log"
    FLUSH_CONNECTIONS = "flush_connections"
    ENABLE_CIRCUIT_BREAKER = "enable_circuit_breaker"
    NOTIFY_ON_CALL = "notify_on_call"
    CREATE_INCIDENT_TICKET = "create_incident_ticket"
    # Medium risk
    SCALE_IN = "scale_in"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    BLOCK_IP_RANGE = "block_ip_range"
    REVOKE_TOKEN = "revoke_token"
    INCREASE_POOL_SIZE = "increase_pool_size"
    # High risk — always requires human approval
    TERMINATE_INSTANCE = "terminate_instance"
    DISABLE_USER_ACCOUNT = "disable_user_account"
    FORCE_FAILOVER = "force_failover"
    DELETE_RESOURCE = "delete_resource"
    MODIFY_IAM_POLICY = "modify_iam_policy"


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


RISK_SCORE_THRESHOLDS = {
    RiskLevel.SAFE: (0.0, 3.0),
    RiskLevel.MODERATE: (3.1, 6.0),
    RiskLevel.HIGH: (6.1, 8.0),
    RiskLevel.CRITICAL: (8.1, 10.0),
}


class ServiceName(str, Enum):
    AUTH_SERVICE = "auth-service"
    PAYMENT_GATEWAY = "payment-gateway"
    FRAUD_ENGINE = "fraud-engine"
    DB_PRIMARY = "db-primary"
    DB_REPLICA = "db-replica"
    CACHE_SERVICE = "cache-service"
    API_GATEWAY = "api-gateway"
    WORKER_SERVICE = "worker-service"
    NOTIFICATION_SERVICE = "notification-service"
    DEPLOYMENT_PIPELINE = "deployment-pipeline"


class SystemLimits:
    MAX_ALERTS_PER_INCIDENT = 50
    MAX_AGENT_RETRIES = 3
    MAX_LLM_TOKENS = 8192
    MAX_CONTEXT_WINDOW_DOCS = 10
    MAX_REMEDIATION_ACTIONS_AUTO = 3
    ALERT_CORRELATION_WINDOW_SECONDS = 300
    INCIDENT_STALE_THRESHOLD_HOURS = 24
    LOG_RETENTION_DAYS = 90
