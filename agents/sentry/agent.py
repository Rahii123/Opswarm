"""
OpsSwarm — Sentry Agent (Stub)
================================
Phase 0: Placeholder. Phase 1 implementation begins here.

Responsibilities:
  - Consume alerts from SQS / Redis Streams
  - Apply anomaly detection rules / ML thresholds
  - Classify severity and event_type
  - Initialise OpsSwarmState and hand off to Correlator
"""

from core.logging_config import get_logger

logger = get_logger(__name__)


class SentryAgent:
    """Anomaly detection agent. Stub — implementation in Phase 1."""

    name = "sentry"

    async def run(self, state: dict) -> dict:
        logger.info("sentry_agent_stub", message="Sentry agent not yet implemented.")
        return state
