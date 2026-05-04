# OpsSwarm Infrastructure Incident Runbook
# ==========================================
# version: "1.0"
# category: infrastructure
# severity: MEDIUM | HIGH | CRITICAL
# services: [worker-service, api-gateway, lambda]
# last_updated: 2024-01-01
# owner: platform-infrastructure-team

## Overview

Covers CPU throttling, memory leaks, disk pressure, and Lambda cold start storms
affecting compute infrastructure across EC2, ECS, and Lambda environments.

---

## Incident Triggers

| Trigger | Threshold | Severity |
|---|---|---|
| CPU utilisation (sustained 5min) | > 80% | HIGH |
| CPU utilisation (sustained 5min) | > 95% | CRITICAL |
| Memory utilisation | > 85% | HIGH |
| Memory utilisation | > 95% | CRITICAL |
| Disk usage | > 80% | MEDIUM |
| Lambda throttle rate | > 5% | HIGH |
| Lambda error rate | > 1% | MEDIUM |
| OOM kill events | Any | CRITICAL |

---

## Investigation Steps

### Step 1 — CPU Analysis

```bash
# Top processes by CPU
top -bn1 | head -20

# Historical CPU (CloudWatch)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxxxxxxxx \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average
```

### Step 2 — Memory Analysis

```bash
# Memory overview
free -h

# Top memory consumers
ps aux --sort=-%mem | head -20

# Check for OOM events
dmesg | grep -i "out of memory" | tail -20
journalctl -k | grep -i "oom" | tail -20
```

### Step 3 — Disk Analysis

```bash
# Disk space
df -h

# Large files/dirs
du -sh /* 2>/dev/null | sort -rh | head -20

# Check for log bloat
du -sh /var/log/*
```

### Step 4 — Lambda Investigation

```bash
# Lambda throttles in last 30 minutes
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=opsswarm-sentry \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum
```

---

## Remediation Procedures

### AUTO-APPROVED Actions (Risk Score 0-3)

**1. Scale Out (Add ECS Tasks)**
```bash
aws ecs update-service \
  --cluster opsswarm-cluster \
  --service worker-service \
  --desired-count 4
```

**2. Rotate Logs to Free Disk Space**
```bash
logrotate -f /etc/logrotate.conf
find /var/log -name "*.log" -mtime +7 -delete
```

**3. Restart Worker Service (Clears Memory Leak)**
```bash
aws ecs update-service \
  --cluster opsswarm-cluster \
  --service worker-service \
  --force-new-deployment
```

### APPROVAL REQUIRED Actions (Risk Score 6+)

**4. Scale In (Remove Tasks)**
- Requires: Engineering lead approval
- Impact: Reduced capacity, potential queue backup
```bash
aws ecs update-service \
  --cluster opsswarm-cluster \
  --service worker-service \
  --desired-count 1
```

**5. Terminate Instance**
- Requires: Engineering lead approval
- Impact: Brief capacity reduction, auto-scaling replaces
```bash
aws ec2 terminate-instances --instance-ids i-xxxxxxxxx
```

---

## Memory Leak Investigation Pattern

For gradual memory leaks (like INC-004):

```python
# Attach to running Python process
import tracemalloc
tracemalloc.start()
# ... reproduce the leak ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

---

## Escalation Path

```
L1: Auto-remediation (scale out, log rotation, restart)
L2: On-call engineer (terminate/replace instance)
L3: Engineering lead (architecture change needed)
```

---

## Related Runbooks

- `db_incident_runbook.md` — If memory leak is in DB layer
- `payment_incident_runbook.md` — If Lambda throttles affect payments
