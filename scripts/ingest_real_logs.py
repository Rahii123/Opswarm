"""
OpsSwarm — Real Log Ingestor
==============================
Reads REAL logs from running Docker containers and passes them
through the full OpsSwarm agent pipeline.

Usage:
    python scripts/ingest_real_logs.py

This script shows you exactly how OpsSwarm would work in production
when connected to a real log source (Docker, CloudWatch, Loki, etc.)
"""

import asyncio
import subprocess
import sys
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env BEFORE importing agents
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from agents.sentry.agent import SentryAgent
from agents.correlator.agent import CorrelatorAgent
from agents.investigator.agent import InvestigatorAgent
from agents.commander.agent import CommanderAgent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def fetch_docker_logs(container_name: str, tail: int = 50) -> list[str]:
    """
    Fetches real logs from a running Docker container.
    This simulates what FluentBit or CloudWatch would do in production.
    """
    try:
        result = subprocess.run(
            ["docker", "logs", container_name, "--tail", str(tail)],
            capture_output=True,
            text=True
        )
        # Docker logs go to stderr by default
        raw = result.stdout + result.stderr
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return lines
    except FileNotFoundError:
        console.print("[red]❌ Docker not found. Make sure Docker Desktop is running.[/red]")
        return []
    except Exception as e:
        console.print(f"[red]❌ Error fetching logs: {e}[/red]")
        return []


def display_log_preview(logs: list[str], container: str):
    """Displays a preview of the fetched real logs."""
    table = Table(title=f"📋 Real Logs from: {container}", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Log Line", style="white")

    for i, line in enumerate(logs[:15], 1):  # Show max 15 lines
        table.add_row(str(i), line[:120])

    if len(logs) > 15:
        table.add_row("...", f"[dim]+{len(logs) - 15} more lines[/dim]")

    console.print(table)


async def run_pipeline_on_real_logs(container_name: str, logs: list[str]):
    """Runs the full OpsSwarm agent pipeline on real Docker logs."""

    console.print(f"\n[bold blue]🐝 Running OpsSwarm pipeline on real logs from '{container_name}'...[/bold blue]\n")

    # Build the initial state — same format as our test script
    state = {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "service_name": container_name,
        "raw_logs": logs,
        "status": "triggered",
        "log_source": "docker_container",   # In production: "cloudwatch" / "loki" / "kafka"
        "last_updated": datetime.now().isoformat()
    }

    # Run through the Swarm
    sentry      = SentryAgent()
    correlator  = CorrelatorAgent()
    investigator = InvestigatorAgent()
    commander   = CommanderAgent()

    console.print("[yellow]Step 1: Sentry Agent analyzing logs...[/yellow]")
    state = await sentry.run(state)
    console.print(f"       → Found [bold]{len(state.get('anomalies', []))}[/bold] anomalies | Severity: [bold red]{state.get('severity', 'N/A').upper()}[/bold red]")

    console.print("[yellow]Step 2: Correlator Agent filtering duplicates...[/yellow]")
    state = await correlator.run(state)
    console.print(f"       → Duplicate: [bold]{state.get('is_duplicate')}[/bold] | Related: {len(state.get('related_incident_ids', []))} incidents")

    console.print("[yellow]Step 3: Investigator Agent performing RCA...[/yellow]")
    state = await investigator.run(state)
    rca = state.get("rca_report", {})
    console.print(f"       → Root Cause: [bold cyan]{rca.get('root_cause', 'N/A')}[/bold cyan]")
    console.print(f"       → Confidence: [bold]{rca.get('confidence', 0) * 100:.0f}%[/bold]")

    console.print("[yellow]Step 4: Commander Agent generating postmortem...[/yellow]")
    state = await commander.run(state)

    # Final Report
    console.print("\n[bold green]✅ Pipeline Complete![/bold green]\n")
    console.print(Panel(
        state.get("postmortem", "No postmortem generated."),
        title=f"📄 Final Postmortem — {container_name}",
        border_style="green",
        expand=False
    ))


async def main():
    console.print("[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")
    console.print("[bold blue]       OpsSwarm — Real Log Ingestion Demo       [/bold blue]")
    console.print("[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]\n")

    # The containers currently running in your OpsSwarm stack
    containers = [
        "opsswarm-postgres",
        "opsswarm-redis",
        "opsswarm-qdrant",
    ]

    console.print("[dim]Fetching real logs from your running Docker containers...[/dim]\n")

    for container in containers:
        console.print(f"[cyan]Fetching logs from container: {container}[/cyan]")
        logs = fetch_docker_logs(container, tail=50)

        if not logs:
            console.print(f"[yellow]⚠️  No logs found for {container}. Is it running? Run: docker-compose up -d[/yellow]\n")
            continue

        console.print(f"[green]✅ Fetched {len(logs)} real log lines[/green]")
        display_log_preview(logs, container)

        await run_pipeline_on_real_logs(container, logs)
        console.print("\n" + "─" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
