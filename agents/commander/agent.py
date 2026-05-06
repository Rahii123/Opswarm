from datetime import datetime
from typing import Dict, Any

from core.logging_config import get_logger

logger = get_logger(__name__)


class CommanderAgent:
    """
    Commander Agent: The "Orchestrator" of OpsSwarm.
    
    Responsibility:
      - Finalizes the incident response lifecycle.
      - Generates the human-readable Postmortem report.
      - Handles final state persistence and external notifications.
    """

    name = "commander"

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution point for the Commander Agent.
        """
        logger.info("commander_finalization_started", incident_id=state.get("incident_id"))
        
        # 1. Generate Postmortem Summary
        postmortem = self._generate_postmortem(state)
        
        # 2. Finalize State
        state["postmortem"] = postmortem
        state["status"] = "resolved" if state.get("severity") != "critical" else "pending_review"
        state["last_updated"] = datetime.utcnow().isoformat()
        state["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(
            "commander_finalization_complete", 
            incident_id=state.get("incident_id"),
            status=state["status"]
        )
        
        return state

    def _generate_postmortem(self, state: Dict[str, Any]) -> str:
        """
        Summarizes the findings into a professional markdown report.
        """
        incident_id = state.get("incident_id", "UNKNOWN")
        service = state.get("service_name", "unknown")
        severity = state.get("severity", "unknown")
        rca = state.get("rca_report", {})
        
        report = f"""
# Incident Postmortem: {incident_id}
**Service:** {service}
**Severity:** {severity.upper()}
**Timestamp:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

## Executive Summary
The OpsSwarm pipeline has completed its autonomous analysis of this incident. 
The system detected {len(state.get('anomalies', []))} anomalies.

## Root Cause Analysis
**Finding:** {rca.get('root_cause', 'N/A')}
**Confidence:** {rca.get('confidence', 0) * 100}%

## Impact
{rca.get('impact_scope', 'N/A')}

## Remediation Plan
**Suggested Action:** {rca.get('suggest_fix', 'N/A')}
**Status:** {state.get('status', 'complete')}

---
*Generated autonomously by OpsSwarm Commander Agent.*
        """
        return report.strip()
