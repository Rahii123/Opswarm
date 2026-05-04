#!/usr/bin/env python3
"""
OpsSwarm — Environment Setup Script
=====================================
Validates the development environment:
  - Python version check
  - Required env vars check
  - Docker service connectivity check
  - Directory structure validation

Usage:
    python scripts/setup_env.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET}   {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}[WARN]{RESET} {msg}")


def header(msg: str) -> None:
    print(f"\n{BOLD}{CYAN}{msg}{RESET}")


def check_python_version() -> bool:
    header("Python Version")
    major, minor = sys.version_info[:2]
    if major == 3 and minor >= 11:
        ok(f"Python {major}.{minor} — OK (3.11+ required)")
        return True
    fail(f"Python {major}.{minor} — FAIL (3.11+ required). Please upgrade.")
    return False


def check_env_file() -> bool:
    header(".env File")
    env_file = ROOT / ".env"
    example_file = ROOT / ".env.example"
    if env_file.exists():
        ok(".env file found")
        return True
    if example_file.exists():
        warn(".env not found — copying from .env.example")
        import shutil
        shutil.copy(example_file, env_file)
        warn("Edit .env and fill in your API keys before proceeding")
        return True
    fail(".env.example missing — repository may be corrupted")
    return False


def check_directory_structure() -> bool:
    header("Directory Structure")
    required_dirs = [
        "agents/sentry", "agents/correlator", "agents/investigator",
        "core", "api/routers", "rag", "infra", "data/incidents",
        "data/runbooks", "tests/unit", "tests/integration",
        "docs", "scripts", "configs",
    ]
    all_ok = True
    for d in required_dirs:
        path = ROOT / d
        if path.exists():
            ok(f"{d}/")
        else:
            fail(f"{d}/ — MISSING")
            all_ok = False
    return all_ok


def check_simulation_data() -> bool:
    header("Simulation Data")
    incidents_dir = ROOT / "data" / "incidents"
    if not incidents_dir.exists():
        fail("data/incidents/ not found — run: python scripts/simulate_incidents.py")
        return False
    incident_files = list(incidents_dir.glob("*.json"))
    if len(incident_files) >= 5:
        ok(f"{len(incident_files)} incident packages found")
        return True
    warn(f"Only {len(incident_files)} incident files found — run: python scripts/simulate_incidents.py")
    return len(incident_files) > 0


def check_docker() -> bool:
    header("Docker Services")
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, cwd=ROOT
        )
        if result.returncode == 0:
            ok("Docker Compose available")
            output = result.stdout.strip()
            if "postgres" in output.lower():
                ok("PostgreSQL container running")
            else:
                warn("PostgreSQL not running — run: docker-compose up -d")
            if "redis" in output.lower():
                ok("Redis container running")
            else:
                warn("Redis not running — run: docker-compose up -d")
            if "qdrant" in output.lower():
                ok("Qdrant container running")
            else:
                warn("Qdrant not running — run: docker-compose up -d")
            return True
        else:
            warn("Docker Compose not available or no services running")
            return False
    except FileNotFoundError:
        fail("Docker not found — install Docker Desktop")
        return False


def main() -> None:
    print(f"\n{BOLD}{'=' * 50}")
    print("  OpsSwarm — Environment Setup Validator")
    print(f"{'=' * 50}{RESET}")

    checks = [
        check_python_version(),
        check_env_file(),
        check_directory_structure(),
        check_simulation_data(),
        check_docker(),
    ]

    passed = sum(checks)
    total = len(checks)

    print(f"\n{BOLD}{'─' * 50}")
    if passed == total:
        print(f"{GREEN}All {total} checks passed. Environment ready!{RESET}")
        print(f"\nNext steps:")
        print(f"  1. docker-compose up -d")
        print(f"  2. pip install -r requirements.txt")
        print(f"  3. python scripts/simulate_incidents.py")
        print(f"  4. uvicorn api.main:app --reload\n")
    else:
        print(f"{YELLOW}{passed}/{total} checks passed. Fix the issues above.{RESET}\n")


if __name__ == "__main__":
    main()
