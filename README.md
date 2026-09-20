# IT Support Agent

Multi-project AI IT/DevOps support engineer for diagnosis, controlled repository fixes and verification.

## Multi-project by design
Projects are configuration, not separate agents. Add projects and repositories in `config/projects.yaml`; paths come from environment variables and are never secrets. The same agent can support DFY, SecureX, TaxiConnect and future client/internal projects.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m cli "List the configured projects"
python -m cli "Investigate the DFY staging login failure. Inspect evidence before changing anything."
```

## Providers
The runtime uses an OpenAI-compatible API abstraction: Groq, OpenAI and Ollama are supported through `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` and optional `LLM_BASE_URL`. No Bedrock or Slack credential is required for the core agent.

## Safety
- Explicit project/repository context.
- Repository-root path confinement prevents traversal.
- Exact unique text replacements for fixes.
- Commands execute with argv and `shell=False`.
- No arbitrary shell tool is exposed to the model.
- No credential rotation, deletion, reboot, deployment or git push is exposed by default.
- Audit events are written to JSONL without storing provider keys.
- Production mutation capabilities should be added as separately permissioned tools with human approval.

## Verification
CI runs Python compilation and pytest. Repository verification can run Python, .NET or Node build checks when the configured project contains the relevant manifest.

## Production readiness
This repository is not declared operationally production-ready merely because CI passes. Before production deployment, configure a real secret manager, durable centralized audit storage, authentication/authorization for any network interface, monitoring/alerting, backups, rate limits, provider failover, and a tested approval workflow. The core multi-project agent is designed so those controls can be added without tying the system to one project.
