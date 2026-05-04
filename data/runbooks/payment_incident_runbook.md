# OpsSwarm Payment Incident Runbook
# ====================================
# version: "1.0"
# category: payments
# severity: HIGH | CRITICAL
# services: [payment-gateway, fraud-engine]
# last_updated: 2024-01-01
# owner: payments-platform-team

## Overview

Covers payment gateway timeouts, cascade failures, fraud detection surges,
and provider-side degradation affecting the payment processing pipeline.

---

## Incident Triggers

| Trigger | Threshold | Severity |
|---|---|---|
| Payment success rate drop | < 95% | HIGH |
| Payment success rate drop | < 85% | CRITICAL |
| P99 payment latency | > 5000ms | HIGH |
| P99 payment latency | > 15000ms | CRITICAL |
| Fraud flags per minute | > 50 (above baseline) | MEDIUM |
| Provider error rate | > 5% | HIGH |
| Retry storm rate | > 3x normal | HIGH |

---

## Investigation Steps

### Step 1 — Check Provider Status

```bash
# Check Stripe status page (always first)
curl -s https://status.stripe.com/api/v2/status.json | python -m json.tool

# Check our provider error breakdown
grep "ERR_PAY" /var/log/payment-gateway/app.log \
  | tail -100 \
  | python -c "import sys,json; [print(json.loads(l)['metadata']['upstream']) for l in sys.stdin]" \
  | sort | uniq -c
```

### Step 2 — Quantify Business Impact

```sql
-- Failed transactions in last 30 minutes
SELECT
  COUNT(*) AS total_attempts,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failures,
  SUM(CASE WHEN status = 'failed' THEN amount_usd ELSE 0 END) AS failed_revenue_usd,
  AVG(processing_time_ms) AS avg_latency_ms
FROM payment_transactions
WHERE created_at > NOW() - INTERVAL '30 minutes';
```

### Step 3 — Detect Retry Storm

```bash
# High retry count = storm in progress
grep "retry_count" /var/log/payment-gateway/app.log \
  | tail -500 \
  | python -c "
import sys, json
retries = [json.loads(l)['metadata'].get('retry_count', 0) for l in sys.stdin]
print(f'Avg retries: {sum(retries)/len(retries):.2f}, Max: {max(retries)}')
"
```

---

## Remediation Procedures

### AUTO-APPROVED Actions (Risk Score 0-3)

**1. Enable Circuit Breaker**
```bash
# Stops retry storm immediately
curl -X POST http://payment-gateway:8080/admin/circuit-breaker/enable \
  -d '{"provider": "stripe", "threshold": 0.5, "timeout": 60}'
```

**2. Notify On-Call + Create Incident Ticket**
- Auto-triggered — payments incidents always page immediately

**3. Switch to Backup Provider (if configured)**
```bash
curl -X POST http://payment-gateway:8080/admin/provider/switch \
  -d '{"primary": "stripe", "fallback": "braintree"}'
```

### APPROVAL REQUIRED Actions (Risk Score 7+)

**4. Pause New Payment Processing**
- Requires: VP Engineering + Finance approval
- Impact: No new transactions accepted — show maintenance page
```bash
curl -X POST http://payment-gateway:8080/admin/maintenance-mode \
  -d '{"enabled": true, "message": "Payment processing temporarily unavailable"}'
```

---

## Retry Storm Prevention

```python
# Correct retry pattern — always use exponential backoff with jitter
import random, time

def retry_with_backoff(fn, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return fn()
        except ProviderError:
            if attempt == max_retries - 1:
                raise
            delay = (base_delay * 2**attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

---

## Escalation Path

```
L1: Auto-remediation (circuit breaker, alerts)
L2: Payments on-call engineer (provider switch)
L3: VP Engineering + Finance (pause processing)
L4: CEO/CFO (if revenue impact > $10k/minute)
```

---

## Related Runbooks

- `infra_incident_runbook.md` — If gateway server is resource-constrained
- `security_incident_runbook.md` — If fraud rate is elevated alongside failures
