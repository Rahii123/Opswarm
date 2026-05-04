"""
OpsSwarm — Incident Simulation Script
=======================================
Generates realistic synthetic incident data for local development
and Sentry agent validation. Produces both raw log streams and
structured incident packages.

Usage:
    python scripts/simulate_incidents.py
    python scripts/simulate_incidents.py --incidents 10 --seed 99
"""

import json
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import track
from rich.table import Table

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = typer.Typer(help="OpsSwarm Incident Simulation Tool")
console = Console()

DATA_DIR = Path(__file__).parent.parent / "data"


# ─── LOG GENERATORS ───────────────────────────────────────────────────────────

def make_timestamp(base: datetime, offset_seconds: int = 0) -> str:
    return (base + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def make_log_entry(
    service: str,
    severity: str,
    event_type: str,
    message: str,
    error_code: str | None,
    timestamp: str,
    host: str = "10.0.1.100",
    region: str = "us-east-1",
    extra_meta: dict | None = None,
) -> dict:
    return {
        "log_id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "service": service,
        "environment": "production",
        "severity": severity,
        "severity_code": {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}[severity],
        "event_type": event_type,
        "message": message,
        "host": host,
        "region": region,
        "trace_id": str(uuid.uuid4()),
        "span_id": uuid.uuid4().hex[:16],
        "error_code": error_code,
        "schema_version": "1.0",
        "metadata": extra_meta or {},
        "alert": {
            "is_alert": severity in ("HIGH", "CRITICAL"),
            "alert_id": str(uuid.uuid4()) if severity in ("HIGH", "CRITICAL") else None,
            "rule_name": f"{event_type}_threshold" if severity in ("HIGH", "CRITICAL") else None,
            "suppressed": False,
        },
    }


# ─── INCIDENT GENERATORS ──────────────────────────────────────────────────────

def generate_brute_force_incident(base_time: datetime) -> dict:
    """INC-001: Sustained brute force authentication attack."""
    logs = []

    # 3 minutes of normal traffic
    for i in range(20):
        logs.append(make_log_entry(
            service="auth-service",
            severity="INFO",
            event_type="authentication_success",
            message=f"User login successful",
            error_code=None,
            timestamp=make_timestamp(base_time, i * 9),
            extra_meta={"user_id": f"user_{random.randint(1000, 9999)}", "latency_ms": random.randint(45, 120)},
        ))

    # Attack begins — 847 failed logins from 12 IPs in 3 minutes
    attacking_ips = [f"185.220.{random.randint(100, 200)}.{random.randint(1, 254)}" for _ in range(12)]
    for i in range(180):
        ip = random.choice(attacking_ips)
        logs.append(make_log_entry(
            service="auth-service",
            severity="CRITICAL" if i % 10 == 0 else "HIGH",
            event_type="authentication_failure",
            message=f"Login failed: invalid credentials for attempted user 'admin' from {ip}",
            error_code="ERR_AUTH_001",
            timestamp=make_timestamp(base_time, 180 + i),
            host="10.0.1.100",
            extra_meta={
                "ip_address": ip,
                "user_agent": "python-requests/2.28.0",
                "attempted_username": "admin",
                "failure_reason": "invalid_credentials",
                "retry_count": i % 5,
                "latency_ms": random.randint(20, 80),
            },
        ))

    return {
        "incident_id": "INC-001",
        "schema_version": "1.0",
        "is_anomaly": True,
        "title": "Brute force authentication attack on auth-service",
        "description": "Sustained credential stuffing attack. 847 failed logins in 3 minutes from 12 distinct IPs targeting the /api/v1/auth/login endpoint.",
        "severity": "CRITICAL",
        "error_code": "ERR_AUTH_001",
        "event_type": "brute_force_attack",
        "affected_service": "auth-service",
        "affected_host": "10.0.1.100",
        "affected_region": "us-east-1",
        "detected_at": make_timestamp(base_time, 180),
        "duration_minutes": 3,
        "expected_root_cause": "Coordinated credential stuffing attack targeting authentication endpoint from 12 distinct external IPs.",
        "expected_remediation": ["block_ip_range", "enable_circuit_breaker", "notify_on_call"],
        "ground_truth_labels": {"is_security_incident": True, "is_automated_attack": True, "requires_human_approval": True},
        "logs": logs,
        "alert_count": sum(1 for l in logs if l["alert"]["is_alert"]),
        "log_count": len(logs),
    }


def generate_db_pool_exhaustion_incident(base_time: datetime) -> dict:
    """INC-002: Database connection pool exhaustion."""
    logs = []

    # Gradual degradation over 8 minutes
    for i in range(40):
        pool_used = min(5 + i * 2, 100)
        severity = "INFO" if pool_used < 60 else ("MEDIUM" if pool_used < 80 else ("HIGH" if pool_used < 95 else "CRITICAL"))
        logs.append(make_log_entry(
            service="db-primary",
            severity=severity,
            event_type="db_pool_exhausted" if pool_used >= 95 else "db_connection_error" if pool_used >= 80 else "db_slow_query",
            message=f"Connection pool usage at {pool_used}% ({pool_used}/100 connections in use)",
            error_code="ERR_DB_001" if pool_used >= 95 else None,
            timestamp=make_timestamp(base_time, i * 12),
            host="db-primary.internal",
            extra_meta={
                "pool_size": 100,
                "active_connections": pool_used,
                "idle_connections": 100 - pool_used,
                "waiting_requests": max(0, pool_used - 90) * 3,
                "avg_query_time_ms": 50 + (pool_used * 2),
            },
        ))

    # Cascade: API starts returning 503
    for i in range(20):
        logs.append(make_log_entry(
            service="api-gateway",
            severity="HIGH",
            event_type="api_5xx_spike",
            message="503 Service Unavailable: upstream database connection timeout",
            error_code="ERR_API_001",
            timestamp=make_timestamp(base_time, 400 + i * 5),
            host="api-gw.internal",
            extra_meta={"upstream": "db-primary", "timeout_ms": 30000, "status_code": 503},
        ))

    return {
        "incident_id": "INC-002",
        "schema_version": "1.0",
        "is_anomaly": True,
        "title": "Database connection pool exhaustion on db-primary",
        "description": "Connection pool gradually exhausted over 8 minutes. Cascade effect causing 503 errors on API Gateway.",
        "severity": "HIGH",
        "error_code": "ERR_DB_001",
        "event_type": "db_pool_exhausted",
        "affected_service": "db-primary",
        "affected_host": "db-primary.internal",
        "affected_region": "us-east-1",
        "detected_at": make_timestamp(base_time, 300),
        "duration_minutes": 8,
        "expected_root_cause": "Runaway query from analytics job holding connections open. Pool exhausted due to no connection timeout configured.",
        "expected_remediation": ["increase_pool_size", "flush_connections", "restart_service"],
        "ground_truth_labels": {"is_security_incident": False, "is_automated_attack": False, "requires_human_approval": False},
        "logs": logs,
        "alert_count": sum(1 for l in logs if l["alert"]["is_alert"]),
        "log_count": len(logs),
    }


def generate_payment_cascade_incident(base_time: datetime) -> dict:
    """INC-003: Payment gateway timeout cascade."""
    logs = []

    for i in range(60):
        timeout_ms = 200 + (i * 50)
        severity = "INFO" if timeout_ms < 2000 else ("MEDIUM" if timeout_ms < 5000 else ("HIGH" if timeout_ms < 15000 else "CRITICAL"))
        logs.append(make_log_entry(
            service="payment-gateway",
            severity=severity,
            event_type="payment_timeout" if timeout_ms > 5000 else "api_latency_high",
            message=f"Payment processing {'timeout' if timeout_ms > 5000 else 'slow'}: {timeout_ms}ms (threshold: 5000ms)",
            error_code="ERR_PAY_001" if timeout_ms > 5000 else None,
            timestamp=make_timestamp(base_time, i * 5),
            host="payment-gw.internal",
            extra_meta={
                "transaction_id": str(uuid.uuid4()),
                "amount_usd": round(random.uniform(10, 500), 2),
                "latency_ms": timeout_ms,
                "upstream": "stripe-api",
                "retry_count": min(i // 10, 3),
            },
        ))

    return {
        "incident_id": "INC-003",
        "schema_version": "1.0",
        "is_anomaly": True,
        "title": "Payment gateway timeout cascade",
        "description": "Payment processing latency escalating from 200ms to 30s+ over 5 minutes. Transactions failing and being retried, causing retry storm.",
        "severity": "CRITICAL",
        "error_code": "ERR_PAY_001",
        "event_type": "payment_cascade",
        "affected_service": "payment-gateway",
        "affected_host": "payment-gw.internal",
        "affected_region": "us-east-1",
        "detected_at": make_timestamp(base_time, 100),
        "duration_minutes": 5,
        "expected_root_cause": "Upstream Stripe API degradation causing timeout cascade. Retry storm amplifying the impact.",
        "expected_remediation": ["enable_circuit_breaker", "notify_on_call", "create_incident_ticket"],
        "ground_truth_labels": {"is_security_incident": False, "is_automated_attack": False, "requires_human_approval": False},
        "logs": logs,
        "alert_count": sum(1 for l in logs if l["alert"]["is_alert"]),
        "log_count": len(logs),
    }


def generate_memory_leak_incident(base_time: datetime) -> dict:
    """INC-004: Gradual memory leak on worker service."""
    logs = []

    for i in range(90):
        mem_pct = 40 + (i * 0.6)
        severity = "INFO" if mem_pct < 70 else ("MEDIUM" if mem_pct < 85 else ("HIGH" if mem_pct < 95 else "CRITICAL"))
        logs.append(make_log_entry(
            service="worker-service",
            severity=severity,
            event_type="memory_leak" if mem_pct > 80 else "api_latency_high",
            message=f"Memory usage at {mem_pct:.1f}% — {'critical: OOM risk' if mem_pct > 90 else 'elevated and growing'}",
            error_code="ERR_INFRA_003" if mem_pct > 80 else None,
            timestamp=make_timestamp(base_time, i * 60),
            host="worker-01.internal",
            extra_meta={
                "memory_percent": round(mem_pct, 1),
                "memory_mb_used": int(mem_pct * 81.92),
                "memory_mb_total": 8192,
                "gc_runs": i * 3,
                "active_threads": 24 + (i // 5),
            },
        ))

    return {
        "incident_id": "INC-004",
        "schema_version": "1.0",
        "is_anomaly": True,
        "title": "Gradual memory leak on worker-service",
        "description": "Memory usage increasing monotonically from 40% to 94% over 90 minutes. GC runs are not reclaiming memory.",
        "severity": "HIGH",
        "error_code": "ERR_INFRA_003",
        "event_type": "memory_leak",
        "affected_service": "worker-service",
        "affected_host": "worker-01.internal",
        "affected_region": "us-east-1",
        "detected_at": make_timestamp(base_time, 2400),
        "duration_minutes": 90,
        "expected_root_cause": "Object accumulation in in-memory job queue. Items enqueued but never dequeued due to a consumer thread deadlock.",
        "expected_remediation": ["restart_service", "scale_out", "notify_on_call"],
        "ground_truth_labels": {"is_security_incident": False, "is_automated_attack": False, "requires_human_approval": False},
        "logs": logs,
        "alert_count": sum(1 for l in logs if l["alert"]["is_alert"]),
        "log_count": len(logs),
    }


def generate_deployment_regression_incident(base_time: datetime) -> dict:
    """INC-005: Deployment regression causing error rate spike."""
    logs = []

    # Pre-deploy: all healthy
    for i in range(15):
        logs.append(make_log_entry(
            service="api-gateway",
            severity="INFO",
            event_type="api_latency_high",
            message="Request processed successfully",
            error_code=None,
            timestamp=make_timestamp(base_time, i * 10),
            extra_meta={"status_code": 200, "latency_ms": random.randint(50, 150), "version": "v2.3.1"},
        ))

    # Deploy v2.3.2 at t+150s
    logs.append(make_log_entry(
        service="deployment-pipeline",
        severity="INFO",
        event_type="health_check_failure",
        message="Deployment started: api-gateway v2.3.2 rolling update initiated",
        error_code=None,
        timestamp=make_timestamp(base_time, 150),
        extra_meta={"version": "v2.3.2", "strategy": "rolling", "replicas": 3},
    ))

    # Post-deploy: error rate spikes
    for i in range(60):
        is_error = random.random() < 0.35
        logs.append(make_log_entry(
            service="api-gateway",
            severity="HIGH" if is_error else "INFO",
            event_type="api_5xx_spike" if is_error else "authentication_success",
            message=f"{'500 Internal Server Error: NullPointerException in UserController.getProfile()' if is_error else 'Request OK'}",
            error_code="ERR_DEPLOY_001" if is_error else None,
            timestamp=make_timestamp(base_time, 180 + i * 5),
            extra_meta={
                "status_code": 500 if is_error else 200,
                "latency_ms": random.randint(1000, 5000) if is_error else random.randint(50, 150),
                "version": "v2.3.2",
                "error": "NullPointerException" if is_error else None,
                "endpoint": "/api/v1/users/profile",
            },
        ))

    return {
        "incident_id": "INC-005",
        "schema_version": "1.0",
        "is_anomaly": True,
        "title": "Deployment regression — v2.3.2 causing 35% error rate spike",
        "description": "API error rate jumped from <1% to 35% immediately after deploying api-gateway v2.3.2. NullPointerException in UserController.",
        "severity": "HIGH",
        "error_code": "ERR_DEPLOY_001",
        "event_type": "deployment_regression",
        "affected_service": "api-gateway",
        "affected_host": "api-gw.internal",
        "affected_region": "us-east-1",
        "detected_at": make_timestamp(base_time, 200),
        "duration_minutes": 5,
        "expected_root_cause": "NullPointerException in UserController.getProfile() introduced in v2.3.2. Null user preference object not handled.",
        "expected_remediation": ["rollback_deployment", "notify_on_call", "create_incident_ticket"],
        "ground_truth_labels": {"is_security_incident": False, "is_automated_attack": False, "requires_human_approval": True},
        "logs": logs,
        "alert_count": sum(1 for l in logs if l["alert"]["is_alert"]),
        "log_count": len(logs),
    }


# ─── MAIN ─────────────────────────────────────────────────────────────────────

GENERATORS = [
    ("INC-001", "Brute Force Auth Attack", generate_brute_force_incident),
    ("INC-002", "DB Pool Exhaustion", generate_db_pool_exhaustion_incident),
    ("INC-003", "Payment Cascade", generate_payment_cascade_incident),
    ("INC-004", "Memory Leak", generate_memory_leak_incident),
    ("INC-005", "Deployment Regression", generate_deployment_regression_incident),
]


@app.command()
def simulate(
    seed: int = typer.Option(42, help="Random seed for reproducibility"),
    output_dir: str = typer.Option(str(DATA_DIR), help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Generate all synthetic incident datasets."""
    random.seed(seed)
    out = Path(output_dir)
    incidents_dir = out / "incidents"
    raw_dir = out / "raw"

    incidents_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    console.rule("[bold cyan]OpsSwarm Incident Simulator[/bold cyan]")
    console.print(f"[dim]Seed: {seed} | Output: {out}[/dim]\n")

    base_time = datetime(2024, 1, 15, 10, 0, 0)
    results = []

    for inc_id, title, generator in track(GENERATORS, description="Generating incidents..."):
        incident = generator(base_time)

        # Write full incident package
        inc_file = incidents_dir / f"{inc_id}_{incident['event_type']}.json"
        with open(inc_file, "w", encoding="utf-8") as f:
            json.dump(incident, f, indent=2, ensure_ascii=False)

        # Write raw logs separately as JSONL
        raw_file = raw_dir / f"{inc_id}_raw_logs.jsonl"
        with open(raw_file, "w", encoding="utf-8") as f:
            for log in incident["logs"]:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")

        results.append((inc_id, title, incident["severity"], incident["log_count"], incident["alert_count"]))
        base_time += timedelta(hours=2)

    # Summary table
    table = Table(title="\n[bold green]Simulation Complete[/bold green]", show_header=True, header_style="bold green")
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Title", style="white", width=40)
    table.add_column("Severity", style="red", width=10)
    table.add_column("Logs", justify="right", width=8)
    table.add_column("Alerts", justify="right", width=8)

    for row in results:
        table.add_row(*[str(v) for v in row])

    console.print(table)
    console.print(f"\n[bold green]Incidents saved to:[/bold green] {incidents_dir}")
    console.print(f"[bold green]Raw logs saved to:[/bold green] {raw_dir}\n")


if __name__ == "__main__":
    app()
