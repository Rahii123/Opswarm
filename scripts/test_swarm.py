import asyncio
import uuid
import sys
import os
from datetime import datetime

# Add the project root to the Python path so it can find the 'agents' folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.sentry.agent import SentryAgent
from agents.correlator.agent import CorrelatorAgent
from agents.investigator.agent import InvestigatorAgent
from agents.commander.agent import CommanderAgent
from rich.console import Console
from rich.panel import Panel

console = Console()

async def run_e2e_test():
    console.print("[bold blue]🐝 Initialising OpsSwarm End-to-End Test...[/bold blue]\n")

    # 1. Setup Mock State (Simulation of a Memory Leak)
    state = {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "service_name": "payment-gateway",
        "raw_logs": [
            "2024-05-07 10:00:01 INFO: System Heartbeat OK",
            "2024-05-07 10:02:45 ERROR: Memory allocation failed in heap",
            "2024-05-07 10:02:46 CRITICAL: java.lang.OutOfMemoryError: Java heap space",
            "2024-05-07 10:02:50 WARN: Garbage collection taking too long (>5s)"
        ],
        "status": "triggered",
        "last_updated": datetime.now().isoformat()
    }

    # 2. Instantiate Agents
    sentry = SentryAgent()
    correlator = CorrelatorAgent()
    investigator = InvestigatorAgent()
    commander = CommanderAgent()

    # 3. Execution Pipeline
    console.print(f"[yellow]Step 1: Running {sentry.name.upper()} Agent...[/yellow]")
    state = await sentry.run(state)

    console.print(f"[yellow]Step 2: Running {correlator.name.upper()} Agent...[/yellow]")
    state = await correlator.run(state)

    console.print(f"[yellow]Step 3: Running {investigator.name.upper()} Agent...[/yellow]")
    state = await investigator.run(state)

    console.print(f"[yellow]Step 4: Running {commander.name.upper()} Agent...[/yellow]")
    state = await commander.run(state)

    # 4. Final Output Evaluation
    console.print("\n[bold green]✅ Swarm Execution Complete![/bold green]\n")
    
    console.print(Panel(
        state.get("postmortem", "No postmortem generated."), 
        title="Final Commander Report", 
        border_style="green",
        expand=False
    ))

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
