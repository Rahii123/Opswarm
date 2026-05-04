-- ============================================================
-- OpsSwarm — PostgreSQL Initialisation Script
-- ============================================================
-- Runs automatically on first docker-compose up.
-- Creates the database schema used by SQLAlchemy ORM.
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id              VARCHAR(64) PRIMARY KEY,
    correlation_id  VARCHAR(36) UNIQUE NOT NULL,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    severity        VARCHAR(16) NOT NULL,
    event_type      VARCHAR(64) NOT NULL,
    error_code      VARCHAR(32),
    affected_service VARCHAR(64) NOT NULL,
    affected_host   VARCHAR(128),
    affected_region VARCHAR(32) DEFAULT 'us-east-1',
    status          VARCHAR(32) NOT NULL DEFAULT 'DETECTED',
    detected_at     TIMESTAMPTZ NOT NULL,
    resolved_at     TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    risk_score      FLOAT,
    risk_level      VARCHAR(16),
    sla_breach_risk BOOLEAN DEFAULT FALSE,
    alert_count     INTEGER DEFAULT 1,
    raw_alert_ids   JSONB,
    service_owner   VARCHAR(128),
    business_impact TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(affected_service);
CREATE INDEX IF NOT EXISTS idx_incidents_detected_at ON incidents(detected_at DESC);

-- RCA Reports table
CREATE TABLE IF NOT EXISTS rca_reports (
    id                      VARCHAR(36) PRIMARY KEY,
    incident_id             VARCHAR(64) NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    root_cause              TEXT NOT NULL,
    root_cause_summary      VARCHAR(512) NOT NULL,
    contributing_factors    JSONB,
    confidence              FLOAT NOT NULL DEFAULT 0.0,
    evidence                JSONB,
    similar_incidents       JSONB,
    recommendations         JSONB,
    generated_by            VARCHAR(64) DEFAULT 'investigator',
    model_used              VARCHAR(128),
    generation_duration_ms  INTEGER,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rca_incident_id ON rca_reports(incident_id);

-- Agent Decisions table
CREATE TABLE IF NOT EXISTS agent_decisions (
    id              VARCHAR(36) PRIMARY KEY,
    incident_id     VARCHAR(64) NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    correlation_id  VARCHAR(36) NOT NULL,
    agent_name      VARCHAR(64) NOT NULL,
    action          VARCHAR(255) NOT NULL,
    rationale       TEXT NOT NULL,
    confidence      FLOAT DEFAULT 0.0,
    risk_score      FLOAT,
    status          VARCHAR(32) DEFAULT 'COMPLETED',
    duration_ms     INTEGER DEFAULT 0,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_incident_id ON agent_decisions(incident_id);
CREATE INDEX IF NOT EXISTS idx_decisions_agent_name ON agent_decisions(agent_name);
CREATE INDEX IF NOT EXISTS idx_decisions_correlation ON agent_decisions(correlation_id);

-- Audit Logs table (append-only — never UPDATE or DELETE)
CREATE TABLE IF NOT EXISTS audit_logs (
    id              VARCHAR(36) PRIMARY KEY,
    correlation_id  VARCHAR(36) NOT NULL,
    incident_id     VARCHAR(64),
    actor           VARCHAR(128) NOT NULL,
    action          VARCHAR(255) NOT NULL,
    resource_type   VARCHAR(64) NOT NULL,
    resource_id     VARCHAR(128),
    before_state    JSONB,
    after_state     JSONB,
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(255),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_incident_id ON audit_logs(incident_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor);

-- Remediations table
CREATE TABLE IF NOT EXISTS remediations (
    id                  VARCHAR(36) PRIMARY KEY,
    incident_id         VARCHAR(64) NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    correlation_id      VARCHAR(36) NOT NULL,
    action              VARCHAR(128) NOT NULL,
    description         TEXT NOT NULL,
    risk_level          VARCHAR(16) NOT NULL,
    risk_score          FLOAT NOT NULL,
    required_approval   BOOLEAN DEFAULT FALSE,
    approved_by         VARCHAR(128),
    approval_timestamp  TIMESTAMPTZ,
    executed            BOOLEAN DEFAULT FALSE,
    executed_at         TIMESTAMPTZ,
    result              TEXT,
    success             BOOLEAN,
    rollback_action     VARCHAR(128),
    rolled_back         BOOLEAN DEFAULT FALSE,
    rolled_back_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_remediations_incident ON remediations(incident_id);

-- Seed a sample incident for health check testing
INSERT INTO incidents (
    id, correlation_id, title, severity, event_type,
    affected_service, status, detected_at
) VALUES (
    'INC-SEED-0001',
    uuid_generate_v4()::VARCHAR,
    'Seed incident for system validation',
    'LOW',
    'system_seed',
    'opsswarm-system',
    'CLOSED',
    NOW()
) ON CONFLICT (id) DO NOTHING;
