# IT Support Agent — Free-Tier Deployment Notes

**Last updated:** 2026-09-20  
**Repository:** `Christopher-Mokolare/it-support-agent`  
**Goal:** $0/month infrastructure using free tiers, while keeping the architecture safe enough for development, demos, low-traffic use, and production-like operation.

> **Important:** A $0 deployment is not the same as a production deployment with an SLA. Render explicitly positions its free compute for testing/hobby/preview use and free services can sleep. Treat this as **free-tier production-like hosting**, not guaranteed production infrastructure.

## 1. Current project direction

The repository was previously split between an older AWS Bedrock/Slack/Lambda architecture and a newer local agent architecture.

The current direction is the newer, provider-agnostic, multi-project agent.

The production-oriented refactor was merged into `main` in PR #1.

Merge commit:

```
821a0b92b26a26c5c176a420ef9a072aed7cb8b4
```

The current application includes:

- Multi-project registry
- Project-specific context
- Safe file inspection
- Path confinement
- Safe command execution
- Exact file replacement
- Verification tools
- Provider abstraction for OpenAI-compatible providers, including Groq/OpenAI/Ollama patterns
- Audit logging
- Bounded agent turns
- CI with Python 3.12, compilation and pytest
- Project configuration for DFY, SecureX and TaxiConnect
- Explicitly restricted production actions

## 2. Target $0 architecture

The intended hosted architecture is:

```text
GitHub
   |
   | source + CI
   v
GitHub Actions
   |
   v
Render Free Web Service
   |
   +----> Supabase Free Postgres
   |
   +----> GitHub API
   |
   +----> Render API
   |
   +----> External LLM provider
```

### Components

| Component | Role | Target cost |
|---|---|---:|
| GitHub | Source control, PRs, CI/CD | $0 |
| GitHub Actions | Tests and automation | $0 within free allowance |
| Render Free Web Service | Hosted agent API | $0 |
| Supabase Free | Persistent database | $0 |
| External LLM | Agent reasoning | $0 only if a suitable free allowance is available |
| Local Ollama | Local development/fallback | $0 |
| GitHub API | Repository inspection and PR workflow | $0 |
| Render API | Service inspection/deployment controls | $0 |

Avoid adding infrastructure that creates unnecessary recurring cost.

## 3. Why the current local-repository implementation cannot simply be deployed

The current local mode uses filesystem paths such as:

```text
~/Documents/GitHub/DFY-BE
~/Documents/GitHub/DFY-FE
...
```

Those paths exist on the developer's computer, not inside a Render container.

Render's filesystem is also ephemeral on free services.

Therefore the hosted version must not depend on the developer's local repository filesystem.

### Required hosted change

Use GitHub as the remote source of truth:

```text
Hosted agent
   |
   v
GitHub API
   |
   +--> read files
   +--> search repository
   +--> create branch
   +--> modify files
   +--> commit
   +--> create PR
   +--> inspect CI
   +--> inspect merge/deploy state
```

The local filesystem tools can remain for local development.

The application should therefore support two modes:

- **Local mode:** local repository paths + Ollama/local tools
- **Hosted mode:** GitHub API + Supabase + external LLM

## 4. Hosted deployment requirements

Before calling the hosted system production-ready, implement all of the following.

### A. HTTP API

The current CLI-oriented agent needs a web API.

Minimum endpoints:

```text
GET  /health
GET  /v1/projects
POST /v1/agent/run
GET  /v1/incidents
GET  /v1/audit
POST /v1/approvals/{id}/approve
POST /v1/approvals/{id}/reject
```

The API must authenticate requests.

### B. Authentication

Do not expose the agent publicly without authentication.

For the first $0 implementation, a server-side API key/header can be used.

Later options include:

- GitHub OAuth
- GitHub App authentication
- A proper identity provider

Never put privileged credentials in browser-side code.

### C. Persistent state

The current JSONL audit file is useful locally but is not suitable as the only hosted audit store.

Use Supabase Postgres for durable state such as:

- projects
- agent runs
- incidents
- approvals
- audit events
- deployment records
- action results
- error/retry state

Do not use Render's ephemeral filesystem for critical state.

### D. GitHub integration

The hosted agent needs a GitHub App or appropriately scoped token.

Prefer least privilege.

The agent should:

1. Read repository state.
2. Diagnose.
3. Create a dedicated branch.
4. Apply changes.
5. Commit.
6. Open a PR.
7. Wait for CI.
8. Report CI status.
9. Require approval before sensitive production actions.
10. Never silently push directly to `main`.

### E. Render integration

The agent should be able to inspect Render services through the Render API.

Potential read operations:

- service status
- deployment status
- recent deploys
- logs where supported
- environment configuration metadata
- health information

Write operations should be approval-gated.

Examples:

- deploy
- rollback
- restart
- environment-variable changes
- destructive operations

### F. Approval workflow

The agent must distinguish between:

**Safe/read actions**

- inspect repository
- read logs
- search code
- inspect service status
- run verification
- explain failures

and:

**Sensitive/write actions**

- merge PR
- deploy
- rollback
- restart
- change secrets
- change production configuration
- delete data
- modify infrastructure

Sensitive actions require an explicit human approval record.

## 5. Recommended production safety model

The model should never have unrestricted shell access on the hosted service.

Prefer explicit tool functions.

Example:

```text
list_projects
read_repository_file
search_repository
create_branch
apply_patch
create_commit
create_pull_request
get_ci_status
get_render_service
get_deployment_status
request_approval
execute_approved_action
```

Do not expose:

```text
arbitrary shell
arbitrary SQL
arbitrary AWS credentials
arbitrary production credential access
unrestricted git push
```

## 6. Secret management

Secrets should be injected as environment variables or managed through the hosting platform.

Typical hosted secrets will include some combination of:

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL

SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY

GITHUB_APP_ID
GITHUB_PRIVATE_KEY
GITHUB_INSTALLATION_ID

RENDER_API_KEY
RENDER_OWNER_ID

ADMIN_API_KEY
```

Exact names should follow the final implementation.

Never commit:

- API keys
- private keys
- JWT secrets
- database passwords
- Render API keys
- GitHub tokens
- provider credentials

The Supabase service-role key must remain server-side.

## 7. Supabase

Use Supabase Free for durable hosted state.

Suggested initial tables:

```text
projects
agent_runs
audit_events
incidents
approvals
deployments
action_results
```

Keep the database schema small initially.

The database should not become a second source of truth for source code. GitHub remains the source of truth for repositories.

## 8. Render

Use one Render Free Web Service for the initial hosted agent.

Advantages:

- Simple deployment
- GitHub integration
- HTTPS
- Health checks
- Custom domain support
- No separate worker required initially

Free-tier constraints must be accepted:

- Service can sleep after inactivity
- Cold starts can occur
- Free compute is limited
- Filesystem is ephemeral
- Free service is not intended by Render as guaranteed production infrastructure
- Resource limits can be reached under sustained workload

Therefore do not build the application around local durable files.

## 9. GitHub Actions

The CI pipeline should at minimum:

1. Install Python 3.12.
2. Install dependencies.
3. Compile the project.
4. Run pytest.
5. Fail on test errors.

Recommended future additions:

- Ruff
- mypy where useful
- dependency/security scanning
- secret scanning
- API tests
- hosted-mode integration tests

GitHub Free provides a monthly Actions allowance for private repositories; public repositories have different hosted-runner treatment. Always verify current GitHub limits before relying on a specific quota.

## 10. LLM strategy

The provider abstraction should remain.

### Local

Use:

```text
Ollama
```

Advantages:

- No API bill
- Good for development
- No cloud model secret required

### Hosted

Use an OpenAI-compatible external provider with a genuinely available free allowance, if available.

Do not hard-code assumptions about free quotas. Provider pricing and free allowances can change.

The hosted application should fail cleanly when the LLM provider is unavailable.

## 11. Free-tier resource safeguards

The agent should protect itself against runaway usage.

Recommended limits:

- maximum agent turns
- maximum command execution time
- maximum file size read
- maximum repository search result size
- maximum API request size
- rate limiting
- request timeout
- retry limit
- exponential backoff
- concurrency limit
- maximum approval lifetime
- maximum log payload
- bounded database queries

## 12. Failure handling

Every external dependency can fail.

Handle:

- GitHub API failure
- Render API failure
- Supabase outage
- LLM timeout
- LLM rate limit
- invalid model response
- CI failure
- deployment failure
- malformed tool arguments
- repository conflict
- branch conflict

The agent should report the failure instead of attempting uncontrolled recovery.

## 13. Observability

Minimum hosted observability:

```text
/health
structured logs
request ID
agent run ID
audit event ID
external operation status
failure reason
duration
```

The database should retain enough information to answer:

- What did the agent do?
- Which project did it operate on?
- Which repository?
- Which user requested it?
- Which tools were called?
- What changed?
- Was approval required?
- Who approved it?
- Did CI pass?
- Was deployment triggered?
- What was the result?

Do not store secrets in audit records.

## 14. Security model

The hosted agent is an operational system, so security is more important than adding more autonomous capabilities.

Required controls:

- authenticated API
- least-privilege GitHub credentials
- server-side secrets
- no arbitrary shell from the LLM
- no unrestricted production push
- approval gates
- audit trail
- rate limiting
- input validation
- bounded tool execution
- safe path handling in local mode
- dependency scanning
- HTTPS
- secure error responses

## 15. Deployment flow

Recommended deployment lifecycle:

```text
Developer changes code
        |
        v
GitHub branch
        |
        v
Pull Request
        |
        v
GitHub Actions
        |
        +---- fail ----> fix
        |
        v
human review/approval
        |
        v
merge to main
        |
        v
Render auto-deploy
        |
        v
health check
        |
        v
deployment recorded
```

The agent should assist with this workflow rather than bypass it.

## 16. Project model

The agent is intended to support multiple projects.

Current project examples:

- DFY
- SecureX
- TaxiConnect

Each project should eventually have:

```yaml
name:
repository:
default_branch:
environment:
render_service:
render_environment:
health_url:
technology:
deployment_policy:
allowed_actions:
```

For hosted mode, repository identity should use GitHub owner/repository information rather than local filesystem paths.

## 17. What is already completed

The production-oriented code refactor already established:

- multi-project registry
- safer tool layer
- path confinement
- bounded command execution
- explicit verification
- provider abstraction
- audit abstraction
- project-specific context
- CI
- tests
- documentation cleanup
- removal of the obsolete Bedrock runtime path from the active architecture

The refactor was merged into `main`.

## 18. What remains before hosted production-like deployment

### Required

- [ ] HTTP API
- [ ] Authentication
- [ ] Supabase integration
- [ ] Supabase schema/migrations
- [ ] GitHub API integration
- [ ] Remote repository tools
- [ ] Branch/PR workflow
- [ ] Render API integration
- [ ] Approval persistence/workflow
- [ ] Persistent audit storage
- [ ] Hosted health endpoint
- [ ] Render deployment configuration
- [ ] Render environment variables
- [ ] Hosted CI/CD
- [ ] Rate limiting
- [ ] Retry/failure handling
- [ ] Security tests
- [ ] API tests
- [ ] End-to-end deployment test

### Recommended

- [ ] GitHub App instead of broad PAT
- [ ] GitHub OAuth
- [ ] deployment rollback workflow
- [ ] structured metrics
- [ ] alerting
- [ ] dependency/security scanning
- [ ] provider failover
- [ ] admin UI
- [ ] incident workflow
- [ ] richer runbook/RAG system

## 19. Definition of done

The system should only be called **production-like deployed** after all of these pass:

1. Render service is reachable.
2. `GET /health` succeeds.
3. Authentication rejects unauthorised requests.
4. An authenticated user can select a project.
5. Agent can inspect the correct GitHub repository.
6. Agent can read/search repository files.
7. Agent can create a branch.
8. Agent can make a controlled change.
9. Agent can create a PR.
10. GitHub Actions passes.
11. Approval is required for protected operations.
12. Approval is recorded.
13. Render deployment succeeds.
14. Deployment health is verified.
15. Audit records are persisted in Supabase.
16. No secrets appear in logs or audit data.
17. Failure paths are tested.
18. Rate limits and timeouts are enforced.
19. The hosted service survives a normal Render restart/cold start.
20. Documentation matches the actual deployment.

## 20. Important $0/month principle

The goal is not to recreate AWS infrastructure on free services.

The goal is:

```text
Keep infrastructure minimal.
Keep state durable.
Keep credentials restricted.
Keep production writes approval-gated.
Keep source code in GitHub.
Keep hosted compute stateless.
Keep the LLM replaceable.
```

This produces a small, understandable DevOps platform rather than a large collection of free-tier services.

## 21. Final architecture target

```text
                         +------------------+
                         |      User        |
                         +--------+---------+
                                  |
                                  v
                         +------------------+
                         | Render Free API  |
                         | Auth + Agent     |
                         +--------+---------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
              v                   v                   v
       +-------------+     +-------------+     +-------------+
       |   GitHub    |     |  Supabase   |     |    LLM      |
       | repos + CI  |     | Postgres    |     | provider    |
       +------+------+     +-------------+     +-------------+
              |
              v
       +-------------+
       |     PR      |
       |   review    |
       +------+------+
              |
              v
       +-------------+
       |    Render   |
       |  deployments|
       +-------------+

Human approval remains required for protected production actions.
```

## 22. Practical next step

The next implementation phase should convert the existing local agent into this hosted architecture without throwing away local development.

Recommended order:

1. Add hosted configuration.
2. Add FastAPI/HTTP layer.
3. Add authentication.
4. Add Supabase persistence.
5. Add GitHub remote repository tools.
6. Add PR/CI workflow.
7. Add Render read-only integration.
8. Add approval workflow.
9. Add protected Render write operations.
10. Add Render deployment configuration.
11. Deploy the first free Render service.
12. Run the full end-to-end test.
13. Only then assess production-like readiness.

