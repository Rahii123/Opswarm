# OpsSwarm Database Incident Runbook
# =====================================
# version: "1.0"
# category: database
# severity: MEDIUM | HIGH | CRITICAL
# services: [db-primary, db-replica, cache-service]
# last_updated: 2024-01-01
# owner: platform-database-team

## Overview

Covers PostgreSQL connection pool exhaustion, replication lag, slow queries,
and OOM (out-of-memory) failures on the primary and replica database nodes.

---

## Incident Triggers

| Trigger | Threshold | Severity |
|---|---|---|
| Connection pool usage | > 80% | HIGH |
| Connection pool usage | > 95% | CRITICAL |
| Replication lag | > 30s | HIGH |
| Replication lag | > 5min | CRITICAL |
| P99 query latency | > 2000ms | MEDIUM |
| P99 query latency | > 10000ms | HIGH |
| Disk usage | > 80% | MEDIUM |
| Disk usage | > 90% | CRITICAL |

---

## Investigation Steps

### Step 1 — Check Connection Pool Status

```sql
-- Current pool state
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;

-- Longest running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '30 seconds'
ORDER BY duration DESC;
```

### Step 2 — Identify Blocking Queries

```sql
-- Find blocking/blocked query pairs
SELECT
  blocked.pid AS blocked_pid,
  blocked.query AS blocked_query,
  blocking.pid AS blocking_pid,
  blocking.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking ON blocking.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted AND blocking_locks.granted;
```

### Step 3 — Check Replication Lag

```sql
-- On primary
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       (sent_lsn - replay_lsn) AS replication_lag_bytes
FROM pg_stat_replication;
```

### Step 4 — Disk Space Check

```bash
df -h /var/lib/postgresql/
du -sh /var/lib/postgresql/data/
```

---

## Remediation Procedures

### AUTO-APPROVED Actions (Risk Score 0-3)

**1. Terminate Long-Running Idle Connections**
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < now() - interval '10 minutes'
  AND pid <> pg_backend_pid();
```

**2. Increase Connection Pool Size (Application Side)**
```bash
# Update environment variable and reload (no restart required)
# PgBouncer pool_size increase
psql -h localhost -U pgbouncer -c "SET pool_size=150;"
```

### APPROVAL REQUIRED Actions (Risk Score 6+)

**3. Kill Blocking Query**
- Requires: DBA approval
```sql
SELECT pg_terminate_backend(<blocking_pid>);
```

**4. Force Failover to Replica**
- Requires: Engineering lead + DBA approval
- Impact: Brief write downtime (30-60 seconds)
```bash
# On replica — promote to primary
pg_ctl promote -D /var/lib/postgresql/data
```

---

## Escalation Path

```
L1: Auto-remediation (flush idle connections, alert)
L2: On-call DBA (kill blocking queries)
L3: Engineering lead (failover decision)
L4: CTO (if data integrity risk)
```

---

## Related Runbooks

- `infra_incident_runbook.md` — If disk/memory is the root cause
- `auth_incident_runbook.md` — If auth DB is specifically impacted
