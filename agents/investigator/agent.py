import json
import os
from datetime import datetime
from typing import List, Dict, Any

from core.logging_config import get_logger
from core.state_schema import RCAReport

logger = get_logger(__name__)


class InvestigatorAgent:
    """
    Investigator Agent: The "Brain" of OpsSwarm.
    
    Phase 1: Heuristic (rule-based) fallback — always works.
    Phase 2: Real LLM (Groq) — activated when GROQ_API_KEY is set in .env
    
    Responsibility:
      - Analyzes anomalies and logs to find the root cause.
      - Uses LLMs to perform logical reasoning over incident data.
      - Produces a structured Root Cause Analysis (RCA) report.
    """

    name = "investigator"

    # Prompt template sent to the LLM
    SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) performing 
Root Cause Analysis (RCA) for infrastructure incidents. 
You will be given log lines and anomaly data. Your job is to analyze them 
and return a JSON object with exactly these fields:
- root_cause: A concise one-sentence explanation of WHY the failure happened.
- impact_scope: Which services or users are affected.
- suggested_fix: The exact remediation action to take.
- confidence: A float between 0.0 and 1.0 representing your certainty.

Respond ONLY with a valid JSON object. No markdown, no explanation."""

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution point for the Investigator Agent."""
        logger.info("investigator_analysis_started", incident_id=state.get("incident_id"))

        logs     = state.get("raw_logs", [])
        anomalies = state.get("anomalies", [])
        service  = state.get("service_name", "unknown")

        # Try real LLM first; fall back to heuristics if key is missing
        groq_api_key = os.getenv("GROQ_API_KEY")

        if groq_api_key:
            logger.info("investigator_mode", mode="LLM (Groq)")
            rca_report = await self._llm_reasoning(service, anomalies, logs, groq_api_key)
        else:
            logger.info("investigator_mode", mode="Heuristic (no GROQ_API_KEY set)")
            rca_report = self._heuristic_reasoning(service, anomalies, logs)

        state["rca_report"]  = rca_report.dict()
        state["status"]      = "investigated"
        state["last_updated"] = datetime.now().isoformat()

        logger.info(
            "investigator_analysis_complete",
            incident_id=state.get("incident_id"),
            confidence=rca_report.confidence
        )
        return state

    # ─── Real LLM Path ────────────────────────────────────────────────────────

    async def _llm_reasoning(
        self, service: str, anomalies: List[Dict], logs: List[str], api_key: str
    ) -> RCAReport:
        """Calls Groq LLM to perform the Root Cause Analysis."""
        try:
            from groq import AsyncGroq

            # Limit logs to 40 lines so we don't exceed token limits
            log_sample = "\n".join(logs[-40:])
            anomaly_summary = json.dumps(anomalies, indent=2)

            user_message = f"""
Service: {service}

Detected Anomalies:
{anomaly_summary}

Log Sample (last 40 lines):
{log_sample}

Analyze the above and return your RCA as a JSON object.
"""
            client = AsyncGroq(api_key=api_key)

            # Read model from .env — never hardcode model names!
            model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.1,   # Low temperature = more deterministic, factual answers
                max_tokens=512,
            )

            raw_text = response.choices[0].message.content.strip()
            data = json.loads(raw_text)

            return RCAReport(
                root_cause   =data.get("root_cause", "LLM did not provide a root cause."),
                impact_scope =data.get("impact_scope", f"Services dependent on {service}."),
                suggested_fix=data.get("suggested_fix", "Investigate further."),
                confidence   =float(data.get("confidence", 0.5)),
                timestamp    =datetime.now().isoformat(),
            )

        except json.JSONDecodeError:
            logger.warning("llm_json_parse_failed", raw=raw_text[:200])
            return self._heuristic_reasoning(service, anomalies, logs)
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            return self._heuristic_reasoning(service, anomalies, logs)

    # ─── Heuristic Fallback Path ───────────────────────────────────────────────

    def _heuristic_reasoning(
        self, service: str, anomalies: List[Dict], logs: List[str]
    ) -> RCAReport:
        """
        Rule-based fallback. Used when GROQ_API_KEY is not set.
        Always reliable — no network calls required.
        """
        root_cause    = "Unknown internal error"
        suggested_fix = "Check service logs and restart container."
        confidence    = 0.5

        anomaly_types = [a.get("type") for a in anomalies]

        if "CRITICAL_SYSTEM_FAILURE" in anomaly_types:
            root_cause    = f"Critical kernel or resource exhaustion in {service}."
            suggested_fix = "Immediate vertical scaling or hardware health check required."
            confidence    = 0.85
        elif "LOG_VOLUME_SPIKE" in anomaly_types:
            root_cause    = f"Traffic surge or logging loop in {service}."
            suggested_fix = "Apply rate limiting or tune logging levels."
            confidence    = 0.75
        elif any("500" in log or "TIMEOUT" in log.upper() for log in logs):
            root_cause    = f"Upstream dependency timeout in {service} layer."
            suggested_fix = "Check connection pooling and circuit breaker settings."
            confidence    = 0.90

        return RCAReport(
            root_cause   =root_cause,
            impact_scope =f"Limited to {service} functionality and downstream consumers.",
            suggested_fix=suggested_fix,
            confidence   =confidence,
            timestamp    =datetime.now().isoformat(),
        )

