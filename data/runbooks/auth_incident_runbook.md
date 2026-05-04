# OpsSwarm Authentication Incident Runbook
# =========================================
# version: "1.0"
# category: security
# severity: HIGH | CRITICAL
# services: [auth-service]
# last_updated: 2024-01-01
# owner: platform-security-team

## Overview

This runbook covers investigation and remediation procedures for authentication-related incidents on the `auth-service`, including brute force attacks, token abuse, and credential stuffing campaigns.

---

## Incident Triggers

| Trigger | Threshold | Severity |
|---|---|---|
| Failed logins per minute | > 50 | HIGH |
| Failed logins per minute | > 200 | CRITICAL |
| Distinct source IPs in 5 min | > 5 | HIGH |
| Token validation errors/min | > 100 | HIGH |
| Account lockouts/min | > 10 | MEDIUM |

---

## Investigation Steps

### Step 1 — Quantify the Attack

```bash
# Count failed logins in last 5 minutes
grep "authentication_failure" /var/log/auth-service/app.log \
  | awk -v d="$(date -d '5 minutes ago' +%Y-%m-%dT%H:%M)" '$0 > d' \
  | wc -l

# List top attacking IPs
grep "authentication_failure" /var/log/auth-service/app.log \
  | grep -oP '"ip_address": "\K[^"]+' \
  | sort | uniq -c | sort -rn | head -20
```

### Step 2 — Identify Target Accounts

```bash
# Most targeted usernames
grep "authentication_failure" /var/log/auth-service/app.log \
  | grep -oP '"attempted_username": "\K[^"]+' \
  | sort | uniq -c | sort -rn | head -10
```

### Step 3 — Check for Successful Compromises

```sql
-- Any successful logins from attacking IPs in last hour?
SELECT user_id, ip_address, created_at
FROM login_events
WHERE ip_address IN ('185.220.x.x', ...)
  AND success = true
  AND created_at > NOW() - INTERVAL '1 hour';
```

### Step 4 — Assess Business Impact

- Are legitimate users being locked out?
- Is the auth-service response time degrading?
- Are downstream services reporting auth failures?

---

## Remediation Procedures

### AUTO-APPROVED Actions (Risk Score 0-3)

**1. Enable Circuit Breaker on /auth/login**
```bash
# Sets a rate limit of 10 requests/IP/minute
curl -X POST http://auth-service:8080/admin/circuit-breaker/enable \
  -d '{"endpoint": "/api/v1/auth/login", "limit": 10, "window": 60}'
```

**2. Notify On-Call**
```bash
# PagerDuty / Slack alert — auto-triggered by Commander agent
```

### APPROVAL REQUIRED Actions (Risk Score 6+)

**3. Block IP Range(s)**
- Requires: Security team approval
- Impact: May block legitimate traffic if IP range is shared (CDN/VPN)
```bash
# AWS WAF rule update
aws wafv2 update-ip-set \
  --scope REGIONAL \
  --id <IP_SET_ID> \
  --addresses "185.220.0.0/16"
```

**4. Revoke All Active Tokens for Affected Accounts**
- Requires: Engineering lead approval
- Impact: Logs out all sessions including legitimate ones
```sql
UPDATE user_sessions
SET revoked = true, revoked_at = NOW(), revoked_reason = 'security_incident'
WHERE user_id IN (SELECT id FROM users WHERE username IN (...));
```

---

## Escalation Path

```
L1: Auto-remediation (circuit breaker, alerts)
L2: On-call engineer (IP blocking decision)
L3: Security team (account compromise confirmed)
L4: CISO + Legal (if PII breach suspected)
```

---

## Post-Incident Actions

- [ ] Generate full IP list for threat intelligence feed
- [ ] Check if credentials appeared in recent breach databases (HaveIBeenPwned API)
- [ ] Review and tighten WAF rules
- [ ] Update anomaly detection thresholds if needed
- [ ] Write postmortem if CRITICAL severity

---

## Related Runbooks

- `db_incident_runbook.md` — If auth DB is impacted
- `security_incident_runbook.md` — For confirmed breaches
