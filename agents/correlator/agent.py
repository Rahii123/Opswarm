from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from core.logging_config import get_logger

logger = get_logger(__name__)


class CorrelatorAgent:
    """
    Correlator Agent: The "Filter" of OpsSwarm.
    
    Responsibility:
      - Groups related alerts to prevent alert fatigue.
      - Suppresses duplicates within a temporal window.
      - Decides if an incoming alert belongs to an existing open incident.
    """

    name = "correlator"
    
    # How far back to look for related incidents (in minutes)
    CORRELATION_WINDOW_MINUTES = 5

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution point for the Correlator Agent.
        """
        logger.info("correlator_analysis_started", incident_id=state.get("incident_id"))
        
        # In a real system, we would query the Database/Redis for open incidents here.
        # For now, we will simulate the correlation logic.
        
        is_duplicate = self._check_for_duplicates(state)
        related_incidents = self._find_related_incidents(state)
        
        if is_duplicate:
            logger.info("correlator_duplicate_suppressed", incident_id=state.get("incident_id"))
            state["is_duplicate"] = True
            state["status"] = "suppressed"
        else:
            state["is_duplicate"] = False
            state["related_incident_ids"] = related_incidents
            state["status"] = "correlated"
            
        state["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(
            "correlator_analysis_complete", 
            incident_id=state.get("incident_id"),
            is_duplicate=state["is_duplicate"],
            related_count=len(related_incidents)
        )
        
        return state

    def _check_for_duplicates(self, state: Dict[str, Any]) -> bool:
        """
        Logic to determine if this alert is an exact duplicate of a very recent one.
        """
        # Placeholder for actual DB lookup logic:
        # SELECT id FROM incidents WHERE service_name = X AND anomaly_type = Y 
        # AND created_at > NOW() - 5m
        
        # For simulation: We'll assume any 'low' confidence anomaly with 
        # identical service name is a potential duplicate.
        anomalies = state.get("anomalies", [])
        if not anomalies:
            return False
            
        # Example logic: If we have multiple identical errors in the same batch
        # we treat them as a single correlated event.
        return False # Default to False for Phase 1 testing

    def _find_related_incidents(self, state: Dict[str, Any]) -> List[str]:
        """
        Finds incidents that are not duplicates but are likely related 
        (e.g., same infrastructure layer).
        """
        related_ids = []
        service = state.get("service_name", "")
        
        # In Phase 2, this would search the Vector Store (Qdrant) 
        # to find "semantically" similar incidents.
        
        # Mock logic: If service is 'database' or 'auth', they are often related.
        if service in ["database", "postgres", "redis"]:
            related_ids.append("INC-GLOBAL-DB-OUTAGE")
            
        return related_ids
