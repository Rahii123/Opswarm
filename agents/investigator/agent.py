from datetime import datetime
from typing import List, Dict, Any, Optional

from core.logging_config import get_logger
from core.state_schema import RCAReport

logger = get_logger(__name__)


class InvestigatorAgent:
    """
    Investigator Agent: The "Brain" of OpsSwarm.
    
    Responsibility:
      - Analyzes anomalies and logs to find the root cause.
      - Uses LLMs to perform logical reasoning over incident data.
      - Produces a structured Root Cause Analysis (RCA) report.
    """

    name = "investigator"

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution point for the Investigator Agent.
        """
        logger.info("investigator_analysis_started", incident_id=state.get("incident_id"))
        
        # 1. Gather Context
        logs = state.get("raw_logs", [])
        anomalies = state.get("anomalies", [])
        service = state.get("service_name", "unknown")
        
        # 2. Perform RCA (Mocked for Phase 1, but ready for LLM integration)
        rca_report = await self._perform_reasoning(service, anomalies, logs)
        
        # 3. Update State
        state["rca_report"] = rca_report.dict()
        state["status"] = "investigated"
        state["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(
            "investigator_analysis_complete", 
            incident_id=state.get("incident_id"),
            confidence=rca_report.confidence
        )
        
        return state

    async def _perform_reasoning(self, service: str, anomalies: List[Dict], logs: List[str]) -> RCAReport:
        """
        This is where the LLM integration happens. 
        In Phase 1, we use a logic-based heuristic to simulate the LLM's conclusion.
        """
        
        # Simulated LLM Prompting Logic:
        # "You are a Senior SRE. Analyze these logs for service {service}..."
        
        root_cause = "Unknown internal error"
        suggested_fix = "Check service logs and restart container."
        confidence = 0.5
        
        # Heuristic reasoning based on Sentry findings
        anomaly_types = [a.get("type") for a in anomalies]
        
        if "CRITICAL_SYSTEM_FAILURE" in anomaly_types:
            root_cause = f"Critical kernel or resource exhaustion in {service}."
            suggested_fix = "Immediate vertical scaling or hardware health check required."
            confidence = 0.85
        elif "LOG_VOLUME_SPIKE" in anomaly_types:
            root_cause = f"Traffic surge or logging loop in {service}."
            suggested_fix = "Apply rate limiting or tune logging levels."
            confidence = 0.75
        elif any("500" in log or "TIMEOUT" in log.upper() for log in logs):
            root_cause = f"Upstream dependency timeout in {service} layer."
            suggested_fix = "Check connection pooling and circuit breaker settings."
            confidence = 0.90

        return RCAReport(
            root_cause=root_cause,
            impact_scope=f"Limited to {service} functionality and downstream consumers.",
            suggested_fix=suggested_fix,
            confidence=confidence,
            analyzed_at=datetime.utcnow().isoformat()
        )
