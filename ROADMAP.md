# IT Support Agent — Project Status & Roadmap

**Last updated:** 2026-09-15
**Status:** Working prototype. LLM backend pluggable (Bedrock / Ollama / Groq). Not yet trusted for autonomous production changes.

---

## What this is

An AI agent that owns the IT support lane end-to-end: triage -> diagnose -> fix -> verify -> document.

Users interact via CLI (Slack planned). It reasons with an LLM, calls sandboxed tools to inspect repos and infrastructure, and gates production changes behind an interactive approval prompt.

The goal is a reliable first-line IT engineer for a solo developer / small team — not a general chatbot, not fully autonomous.


---

## Architecture

```
CLI: python agent.py "your request"
      |
agent.py  (single file)
      |
LLM backend (LLM_PROVIDER env var)
  bedrock / ollama / groq
      |
Tools (sandboxed)
  scan_repo, read_file, apply_fix,
  git_commit_and_push, get_logs, lookup_runbook
      |
agent_audit.log  (JSONL, every tool call)
```

### Guardrails in place

- File paths confined to REPOS roots - no ../ escapes
- Subprocess calls use argv lists, shell=False - no shell injection
- git_commit_and_push on PROD_REPOS blocks for interactive "yes"
- Every tool call appended to agent_audit.log

---

## What works today

- Single-file agent, no external services for CLI use
- Tool-calling loop with OpenAI-compatible backends
- Sandboxed file read/write confined to two repos
- Approval gate before production pushes
- Audit log
- Read-only CloudWatch Logs Insights queries
- Local runbook RAG (keyword-scored markdown)
- bootstrap.sh for reproducible setup

## What does NOT work yet

- LLM provider patch may not be applied - verify with: `grep LLM_PROVIDER agent.py`
- Bedrock path dead - AWS account closed; function kept for reference
- Ollama download incomplete (connection too slow, ~350 KB/s)
- No Slack interface - block commented at bottom of agent.py
- No ticketing tool
- No EC2 / IAM mutations - deferred (high blast radius)
- No tests
- runbooks/ has one stub; RAG has nothing meaningful to retrieve


---

## How to continue

### Immediate

1. Pick an LLM backend and make it work.
   - Groq: free key at https://console.groq.com/keys
   - Ollama: finish `ollama pull qwen2.5-coder:7b-instruct-q4_K_M`
2. Commit the working state.
3. Write 5-10 runbooks under runbooks/.

### Short term

4. create_ticket tool -> local SQLite (tickets.db)
5. Ensure provider-agnostic run_agent is the one running
6. --dry-run flag: apply_fix and git_commit_and_push log intent without writing
7. tests/test_tools.py covering path sandboxing

### Medium term

8. Slack interface with signature verification + reaction approval
9. Dockerfile
10. Move to VPS (Hetzner CX22 ~EUR4/mo, or Oracle Cloud always-free ARM)
11. EC2 / IAM tools with separate approval gates + dry-run preview

### Long term

12. Real vector store for RAG if runbooks > 50 files
13. Web UI if teammates need access
14. Metrics: latency, token usage, approval rate, success rate

---

## Known risks

| Risk | Severity | Mitigation |
|---|---|---|
| LLM misapplies fix to wrong file | Medium | old_str must match uniquely; approval gate |
| Agent reads .env via read_file | Low | read_file confined to REPOS; .env outside |
| Groq sees source code | Medium | Use Ollama for sensitive repos |
| Slack token leak -> unauthorized use | High (when Slack on) | Signature verification, user allow-list |
| Agent commits broken code | Medium | Re-scan after fix; approval gate |
| Audit log grows unbounded | Low | Rotate monthly |

---

## Provider comparison (2026-09)

| Provider | Cost | Quality | Privacy | Setup |
|---|---|---|---|---|
| Bedrock Claude Sonnet 4.5 | ~0.10 USD/task | Best | AWS | Blocked |
| Groq Llama 3.3 70B | Free tier | Very good | Groq servers | 2 min |
| Ollama Qwen2.5-Coder 7B | Free | Good | Local | Slow download |
| Ollama Qwen2.5-Coder 14B | Free | Very good | Local | Needs 16 GB+ |

8 GB Mac ceiling: 7B local. Better local quality needs more RAM or a VPS.

---

## Setup from scratch

```
git clone git@github.com:Christopher-Mokolare/it-support-agent.git
cd it-support-agent
bash bootstrap.sh
# edit .env, set LLM_PROVIDER and keys
python agent.py "scan DFY-FE and tell me what is broken"
```

---

## Open questions

- Should the agent commit without a second human review? Currently: yes, with interactive "yes".
- Where should tickets live? SQLite next.
- How much autonomy on "fix broken build on main"? Currently gated.

---

## Changelog

- 2026-09-15 - single-file rewrite, sandboxed tools, audit log, approval gate, bootstrap.sh, this roadmap. Bedrock account closed; pivot to pluggable providers.
- 2026-09-15 (earlier) - initial repo commit, terraform lock, single-file agent.
- 2026-08-04 - original multi-file design (Bedrock Agents, Lambda, DynamoDB, Knowledge Base).
