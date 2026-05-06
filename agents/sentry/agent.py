import re
from datetime import datetime
from typing import List, Dict, Any

from core.logging_config import get_logger
from core.state_schema import AnomalyDetails

logger = get_logger(__name__)
 

class SentryAgent:
    """
    Sentry Agent: The "Watchtower" of OpsSwarm.
    
    Responsibility:
      - Analyzes raw logs and metrics.
      - Detects patterns, spikes, and high-risk keywords.
      - Calculates initial severity and triggers the response pipeline.
    """

    name = "sentry"

    # Keywords that trigger immediate high-priority analysis
    CRITICAL_KEYWORDS = [
        "FATAL", "CRITICAL", "PANIC", "OUT_OF_MEMORY", 
        "OOM", "SEGFAULT", "DEADLOCK", "EXPIRED_CERTIFICATE"
    ]
    
    ERROR_KEYWORDS = ["ERROR", "EXCEPTION", "FAILED", "TIMEOUT", "500", "503"]

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution point for the Sentry Agent in the LangGraph workflow.
        """
        logger.info("sentry_analysis_started", incident_id=state.get("incident_id"))
        
        raw_logs = state.get("raw_logs", [])
        service_name = state.get("service_name", "unknown")
        
        # 1. Perform Anomaly Detection
        anomalies = self._detect_anomalies(raw_logs)
        
        # 2. Determine Severity based on anomalies found
        severity = self._calculate_severity(anomalies)
        
        # 3. Update State
        state["anomalies"] = [a.dict() for a in anomalies]
        state["severity"] = severity
        state["status"] = "analyzed"
        state["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(
            "sentry_analysis_complete", 
            incident_id=state.get("incident_id"),
            anomalies_found=len(anomalies),
            final_severity=severity
        )
        
        return state

    def _detect_anomalies(self, logs: List[str]) -> List[AnomalyDetails]:
        """
        Scans log lines for known error patterns and keywords.
        """
        detected_anomalies = []
        
        for line in logs:
            # Check for Critical Anomaly
            if any(keyword in line.upper() for keyword in self.CRITICAL_KEYWORDS):
                detected_anomalies.append(
                    AnomalyDetails(
                        type="CRITICAL_SYSTEM_FAILURE",
                        description=f"High-priority failure detected: {line[:100]}...",
                        confidence=0.95
                    )
                )
                continue
            
            # Check for Standard Error Anomaly
            if any(keyword in line.upper() for keyword in self.ERROR_KEYWORDS):
                detected_anomalies.append(
                    AnomalyDetails(
                        type="APPLICATION_ERROR",
                        description=f"Standard error detected: {line[:100]}...",
                        confidence=0.85
                    )
                )

        # Statistical Anomaly (Example: Log volume check)
        if len(logs) > 500:
            detected_anomalies.append(
                AnomalyDetails(
                    type="LOG_VOLUME_SPIKE",
                    description=f"Unusual log volume detected: {len(logs)} lines in single burst.",
                    confidence=0.70
                )
            )

        return detected_anomalies

    def _calculate_severity(self, anomalies: List[AnomalyDetails]) -> str:
        """
        Heuristic-based severity calculation.
        """
        if not anomalies:
            return "low"
            
        types = [a.type for a in anomalies]
        
        if "CRITICAL_SYSTEM_FAILURE" in types:
            return "critical"
        
        if types.count("APPLICATION_ERROR") > 5 or "LOG_VOLUME_SPIKE" in types:
            return "high"
            
        if "APPLICATION_ERROR" in types:
            return "medium"
            
        return "low"
