# OpsSwarm — AWS Infrastructure Reference
## Cloud Resource Definitions & Build Order

> This document defines every AWS resource needed for OpsSwarm,
> organised by build phase. Use this as your Terraform and AWS Console checklist.

---

## Phase 1 — IAM (Build First — Everything Depends on This)

### IAM Roles

| Role Name | Used By | Key Permissions |
|---|---|---|
| `OpsSwarmLambdaRole` | Lambda functions | DynamoDB R/W, SQS consume/send, S3 R/W, CloudWatch logs |
| `OpsSwarmECSRole` | ECS task containers | Same as Lambda + Secrets Manager read |
| `OpsSwarmAPIGatewayRole` | API Gateway | Lambda invoke |
| `OpsSwarmCICDRole` | GitHub Actions / CodePipeline | ECR push, ECS update-service, S3 sync |

### IAM Policies (Least Privilege)

```json
// OpsSwarmDynamoDBPolicy — attach to Lambda and ECS roles
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
        "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/opsswarm-*"
      ]
    }
  ]
}
```

---

## Phase 2 — KMS & Secrets Manager

| Resource | Purpose |
|---|---|
| KMS Key: `opsswarm-main` | Encrypt DynamoDB, S3, SQS at rest |
| Secret: `opsswarm/production/postgres` | RDS password |
| Secret: `opsswarm/production/api-keys` | LLM API keys (Groq, Gemini) |
| Secret: `opsswarm/production/qdrant` | Qdrant API key |

> **Rule:** Never put secrets in Lambda environment variables. Always use Secrets Manager.

---

## Phase 3 — S3 Buckets

| Bucket Name | Purpose | Config |
|---|---|---|
| `opsswarm-artifacts-{account-id}` | Incident JSON packages, RCA reports | Versioning ON, AES-256, Block all public |
| `opsswarm-reports-{account-id}` | Final postmortem PDFs, dashboards | Versioning ON, AES-256, Block all public |
| `opsswarm-terraform-state-{account-id}` | Terraform remote state | Versioning ON, MFA delete ON |

```bash
# Create artifact bucket
aws s3api create-bucket \
  --bucket opsswarm-artifacts-$(aws sts get-caller-identity --query Account --output text) \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket opsswarm-artifacts-ACCOUNT_ID \
  --versioning-configuration Status=Enabled

# Block all public access
aws s3api put-public-access-block \
  --bucket opsswarm-artifacts-ACCOUNT_ID \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## Phase 4 — DynamoDB Tables

### Table 1: `opsswarm-workflow-state`
```
Partition Key: incident_id (String)
Sort Key:      step_name (String)
Billing:       PAY_PER_REQUEST
Encryption:    AWS_OWNED_CMK
TTL Attribute: expires_at
```

### Table 2: `opsswarm-agent-memory`
```
Partition Key: agent_id (String)
Sort Key:      timestamp (String, ISO-8601)
Billing:       PAY_PER_REQUEST
TTL Attribute: expires_at
```

### Table 3: `opsswarm-incident-lifecycle`
```
Partition Key: incident_id (String)
Billing:       PAY_PER_REQUEST
```

```bash
# Create workflow state table
aws dynamodb create-table \
  --table-name opsswarm-workflow-state \
  --attribute-definitions \
      AttributeName=incident_id,AttributeType=S \
      AttributeName=step_name,AttributeType=S \
  --key-schema \
      AttributeName=incident_id,KeyType=HASH \
      AttributeName=step_name,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true
```

---

## Phase 5 — SQS Queues

| Queue Name | Type | Purpose | DLQ |
|---|---|---|---|
| `opsswarm-alert-ingest.fifo` | FIFO | Deduplicated alert ingestion | `opsswarm-alert-ingest-dlq.fifo` |
| `opsswarm-agent-tasks.fifo` | FIFO | Ordered agent task dispatch | `opsswarm-agent-tasks-dlq.fifo` |
| `opsswarm-approval-requests` | Standard | Human approval notifications | `opsswarm-approval-dlq` |
| `opsswarm-remediation-results` | Standard | Post-remediation status | `opsswarm-remediation-dlq` |

> **Rule:** Every queue must have a DLQ with 14-day retention. Silent failures are unacceptable.

```bash
# Create FIFO queue with DLQ
aws sqs create-queue \
  --queue-name opsswarm-alert-ingest-dlq.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true

aws sqs create-queue \
  --queue-name opsswarm-alert-ingest.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true,\
RedrivePolicy='{"deadLetterTargetArn":"arn:aws:sqs:us-east-1:ACCOUNT:opsswarm-alert-ingest-dlq.fifo","maxReceiveCount":"3"}'
```

---

## Phase 6 — EventBridge

| Event Bus | Rule | Target |
|---|---|---|
| `opsswarm-events` | `severity = CRITICAL` | SNS topic → PagerDuty |
| `opsswarm-events` | `event_type = deployment_regression` | SQS alert-ingest |
| `opsswarm-events` | `approval_required = true` | SQS approval-requests |

---

## Phase 7 — Lambda Functions (Stubs First)

| Function | Runtime | Memory | Timeout | Trigger |
|---|---|---|---|---|
| `opsswarm-sentry` | Python 3.11 | 512 MB | 60s | SQS alert-ingest |
| `opsswarm-correlator` | Python 3.11 | 256 MB | 30s | SQS agent-tasks |
| `opsswarm-investigator` | Python 3.11 | 1024 MB | 300s | SQS agent-tasks |
| `opsswarm-remediator` | Python 3.11 | 256 MB | 60s | SQS agent-tasks |
| `opsswarm-commander` | Python 3.11 | 512 MB | 120s | SQS agent-tasks |

> **Lambda Architecture Rules:**
> - Always configure reserved concurrency (prevent runaway costs)
> - Always set DLQ on every Lambda
> - Use Lambda Layers for shared dependencies (core/, rag/)
> - Never put secrets in environment variables — use Secrets Manager

---

## Phase 8 — API Gateway

```
Type:          HTTP API (cheaper than REST API)
Endpoint:      Regional
Stage:         $default (auto-deploy)
CORS:          Configured per endpoint
Auth:          JWT authorizer (future — Phase 5)
Throttling:    10,000 req/s burst, 5,000 req/s steady
```

---

## Phase 9 — CloudWatch

### Log Groups (create before Lambdas)
```bash
aws logs create-log-group --log-group-name /opsswarm/api
aws logs create-log-group --log-group-name /opsswarm/agents/sentry
aws logs create-log-group --log-group-name /opsswarm/agents/investigator
aws logs create-log-group --log-group-name /opsswarm/agents/remediator

# Set 90-day retention on all
aws logs put-retention-policy --log-group-name /opsswarm/api --retention-in-days 90
```

### Alarms (Critical Ones)

| Alarm | Metric | Threshold | Action |
|---|---|---|---|
| `SentryLambdaErrors` | Lambda Errors | > 5 in 5min | SNS → email |
| `AlertIngestDLQDepth` | SQS ApproximateNumberOfMessages | > 0 | SNS → PagerDuty |
| `APIGateway5xxRate` | 5XXError | > 1% | SNS → email |
| `DynamoDBThrottles` | ThrottledRequests | > 0 | SNS → email |

---

## Free Tier Budget Tracker

| Service | Free Tier | Expected Dev Usage |
|---|---|---|
| Lambda | 1M requests + 400K GB-sec/month | ~50K requests — ✅ Free |
| DynamoDB | 25 GB + 25 WCU/RCU | < 1 GB + < 5 WCU — ✅ Free |
| SQS | 1M requests/month | ~100K — ✅ Free |
| S3 | 5 GB + 20K GET + 2K PUT | < 1 GB — ✅ Free |
| CloudWatch | 10 metrics + 5 GB logs | Within limits — ✅ Free |
| API Gateway | 1M HTTP API calls/month | < 100K — ✅ Free |

> **Note:** RDS PostgreSQL is NOT free tier. Use Docker local Postgres in dev.
> Only provision RDS when deploying to staging/production.
