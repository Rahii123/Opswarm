# OpsSwarm 🐝
### Autonomous Incident Response & Root Cause Analysis Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

OpsSwarm is an enterprise-grade AIOps platform that autonomously monitors cloud infrastructure, detects anomalies, performs root cause analysis (RCA), and executes safe remediation workflows with human oversight when required.

It solves the core operational challenges modern engineering teams face:

| Challenge | OpsSwarm Solution |
|---|---|
| Alert fatigue | Correlator Agent — smart grouping & suppression |
| Slow incident triage | Sentry Agent — sub-minute anomaly detection |
| High MTTR | Investigator Agent — automated root cause analysis |
| Inconsistent remediation | Safe Action Library + Guardrails |
| Complex RCA | Context Builder + RAG knowledge retrieval |
| Audit gaps | Commander Agent — full audit trail & postmortems |

---

## Architecture

```
Alerts/Logs/Metrics
        │
        ▼
  ┌─────────────┐
  │ Sentry Agent │  ← Anomaly Detection
  └──────┬──────┘
         │
  ┌──────▼──────────┐
  │ Correlator Agent │  ← Alert Grouping & Suppression
  └──────┬───────────┘
         │
  ┌──────▼──────────────┐
  │ Context Builder Agent │  ← Incident Enrichment
  └──────┬───────────────┘
         │
  ┌──────▼──────────┐
  │ Investigator Agent │  ← Root Cause Analysis
  └──────┬────────────┘
         │
  ┌──────▼──────────┐
  │ Decision Router  │  ← Risk Scoring & Routing
  └──────┬──┬────────┘
         │  │
   Safe  │  │  Risky
         │  │
  ┌──────▼┐ ┌▼──────────────┐
  │Remedia│ │Human Approval  │
  │tor    │ │Workflow        │
  └──────┬┘ └┬──────────────┘
         │   │
  ┌──────▼───▼──┐
  │  Commander   │  ← RCA Report + Audit Trail
  └─────────────┘
```

---

## Tech Stack

### AI / Orchestration
- **LangGraph** — Stateful multi-agent orchestration
- **Groq / Gemini / OpenRouter** — LLM providers (configurable)
- **Qdrant** — Vector store for RAG knowledge retrieval
- **LangFuse** — LLM observability & tracing

### Backend
- **FastAPI** — REST API layer
- **PostgreSQL** — Relational operational store
- **Redis** — Event streams & distributed caching
- **SQLAlchemy** — ORM with async support

### Cloud (AWS)
- **Lambda** — Serverless agent execution
- **DynamoDB** — Workflow state persistence
- **SQS / EventBridge** — Event-driven messaging
- **S3** — Artifact & report storage
- **CloudWatch** — Metrics & log aggregation
- **API Gateway** — Public API endpoint

### Observability
- **Grafana** — Operational dashboards
- **Prometheus** — Metrics collection
- **LangFuse** — Agent trace observability

---

## Project Structure

```
OpsSwarm/
├── agents/          # Autonomous agent implementations
├── core/            # Shared utilities & schemas
├── rag/             # RAG pipeline & vector store
├── api/             # FastAPI application layer
├── infra/           # Infrastructure-as-Code (Terraform)
├── dashboards/      # Grafana & Prometheus configs
├── tests/           # Full test suite
├── data/            # Synthetic datasets & runbooks
├── configs/         # Environment configuration files
├── docs/            # Technical documentation
└── scripts/         # Dev automation scripts
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- AWS CLI (configured)
- Git

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/opsswarm.git
cd OpsSwarm
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Local Infrastructure

```bash
docker-compose up -d
# Starts: PostgreSQL, Redis, Qdrant
```

### 3. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python scripts/seed_db.py
```

### 5. Run Simulation Data

```bash
python scripts/simulate_incidents.py
```

### 6. Start API Server

```bash
uvicorn api.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

---

## Safety Framework

OpsSwarm is built **safety-first**. No automated action is executed without:

1. **Risk scoring** — Every action scored 0-10 before execution
2. **Safe Action Library** — Whitelist of pre-approved low-risk actions
3. **Human-in-the-loop** — All actions scoring > 6 require explicit approval
4. **Audit trail** — Every decision logged with rationale, confidence, and actor
5. **Rollback capability** — All remediations include rollback plan before execution

---

## Development Phases

| Phase | Status | Description |
|---|---|---|
| Phase 0: Foundation | ✅ In Progress | Monorepo, config, DB models, simulation data |
| Phase 1: Sentry Agent | 🔲 Planned | Anomaly detection on simulated data |
| Phase 2: Correlator Agent | 🔲 Planned | Alert grouping & suppression |
| Phase 3: Context Builder | 🔲 Planned | Incident enrichment via RAG |
| Phase 4: Investigator | 🔲 Planned | LLM-powered root cause analysis |
| Phase 5: Decision Router | 🔲 Planned | Risk scoring engine |
| Phase 6: Remediator | 🔲 Planned | Safe action execution |
| Phase 7: Commander | 🔲 Planned | RCA reports & postmortems |
| Phase 8: AWS Deployment | 🔲 Planned | Full cloud deployment |

---

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## License

MIT License — see [LICENSE](LICENSE)
