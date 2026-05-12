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

    # ── Anti-Hallucination Prompt (Grounded) ────────────────────────────────
    # Key rules enforce evidence-based reasoning and prevent the LLM from
    # inventing problems that don't exist in the actual log data.
    SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) performing
Root Cause Analysis (RCA) for infrastructure incidents.

You will be given:
  1. A list of detected anomalies (may be empty)
  2. Raw log lines from the service

Your STRICT rules:
  - ONLY use evidence that is EXPLICITLY present in the provided logs.
  - If the anomaly list is EMPTY and the logs show no errors, warnings, or failures,
    you MUST set root_cause to "No incident detected" and confidence to 0.1.
  - NEVER infer a failure from startup or informational messages (INFO logs).
  - Normal operations (CREATE TABLE, INFO, starting services) are NOT incidents.
  - Do NOT assume a problem if one is not clearly evidenced by ERROR, CRITICAL,
    FATAL, WARN with failure context, or explicit exception messages.
  - The word "Initializing" means starting fresh — it is NOT a failure.

Return a JSON object with exactly these fields:
  - root_cause: One sentence citing specific evidence from the logs.
  - impact_scope: Which services or users are affected (or "None" if no incident).
  - suggested_fix: Exact remediation action, or "No action required" if healthy.
  - confidence: Float 0.0-1.0. Use low values (< 0.3) when logs show no errors.

Respond ONLY with a valid JSON object. No markdown, no extra text."""

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

        # ── Confidence Thresholding (Anti-Hallucination Safety Net) ───────────
        # Rule: If Sentry found ZERO anomalies AND the LLM still claims high
        # confidence about a problem, the LLM is hallucinating.
        # Override its conclusion to protect against false positives.
        if len(anomalies) == 0 and rca_report.confidence >= 0.75:
            logger.warning(
                "confidence_threshold_override",
                reason="Sentry found 0 anomalies but LLM claimed high confidence — likely hallucination",
                original_confidence=rca_report.confidence,
                original_root_cause=rca_report.root_cause,
            )
            rca_report.root_cause    = "No incident detected — service logs show normal operation."
            rca_report.suggested_fix = "No action required."
            rca_report.impact_scope  = "None"
            rca_report.confidence    = 0.1

        state["rca_report"]  = rca_report.dict()
        state["status"]      = "investigated"
        state["last_updated"] = datetime.now().isoformat()

        logger.info(
            "investigator_analysis_complete",
            incident_id=state.get("incident_id"),
            confidence=rca_report.confidence,
            anomalies_count=len(anomalies)
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

            # Tell the LLM explicitly when there are no anomalies
            anomaly_context = (
                f"Detected Anomalies (from Sentry Agent):\n{anomaly_summary}"
                if anomalies
                else "Detected Anomalies: NONE — The Sentry Agent found zero anomalies in these logs."
            )

            user_message = f"""Service Under Analysis: {service}

{anomaly_context}

Raw Log Sample (last 40 lines):
{log_sample}

IMPORTANT REMINDER:
- If there are no anomalies and logs show only INFO messages, return confidence <= 0.2
- Only cite evidence that is EXPLICITLY in the logs above
- "Initializing" and "Starting" are healthy startup messages, NOT failures

Return your RCA as a JSON object.
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
                temperature=0.0,   # Zero temperature = maximum determinism, no creative guessing
                max_tokens=512,
            )

            raw_text = response.choices[0].message.content.strip()
            # Strip markdown code blocks if LLM ignores instructions
            # e.g. ```json { ... } ``` → { ... }
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()
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

