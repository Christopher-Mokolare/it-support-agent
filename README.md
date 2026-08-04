# IT Support Agent

An AI agent that **owns the IT support lane end-to-end** — triage, diagnose, fix, verify, document.

## Architecture

```
Slack mention
     ↓
main.py (Slack Socket Mode)
     ↓
Amazon Bedrock Agent (Claude 3.5 Sonnet)
     ↓ (tool calls)
Lambda action_handler.py
     ↓
┌─────────────────────────────────────┐
│  ticket_tool  │  infra_tool         │
│  logs_tool    │  runbook_tool (RAG) │
└─────────────────────────────────────┘
     ↓
DynamoDB (tickets) │ CloudWatch │ EC2/IAM │ S3+OpenSearch (runbooks)
```

## Setup

### 1. Deploy infrastructure
```bash
cd infra
terraform init
terraform apply
```

### 2. Upload runbooks to S3
```bash
aws s3 cp ./runbooks/ s3://<your-bucket>/ --recursive
```

### 3. Create Bedrock Knowledge Base
```python
from memory.knowledge_base import create_knowledge_base, sync_knowledge_base
kb = create_knowledge_base(role_arn="...", bucket_name="...", collection_arn="...")
sync_knowledge_base(kb["knowledgeBaseId"], data_source_id="...")
```

### 4. Create Bedrock Agent
```python
from agent.bedrock_agent import create_agent
agent = create_agent(role_arn="<bedrock-role-arn>", knowledge_base_id="<kb-id>")
```

### 5. Configure environment
```bash
cp .env.example .env
# fill in BEDROCK_AGENT_ID, BEDROCK_AGENT_ALIAS_ID, SLACK tokens
```

### 6. Run
```bash
pip install -r requirements.txt
python main.py
```

## Usage (Slack)

```
@it-support my EC2 instance i-0abc123 is unreachable
@it-support rotate access keys for user john.doe
@it-support show me errors in /aws/lambda/payments-service from the last 2 hours
@it-support create a ticket: CI pipeline failing on main branch, severity high
```

## What the agent owns

| Capability | Tool |
|---|---|
| Ticket lifecycle | DynamoDB via ticket_tool |
| EC2 status & reboot | EC2 API via infra_tool |
| IAM key rotation | IAM API via infra_tool |
| Log analysis | CloudWatch Insights via logs_tool |
| Runbook lookup | Bedrock Knowledge Base via runbook_tool |

## Guardrails
- Production changes → agent summarizes plan, waits for human ✅ approval in Slack
- All actions logged to ticket history
- Lambda IAM role follows least privilege
