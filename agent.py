#!/usr/bin/env python3
"""Single-file IT support agent. CLI: python agent.py "your request"."""

from __future__ import annotations
import json, logging, os, re, subprocess, sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")
MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "12"))
AUDIT_LOG = Path(os.getenv("AGENT_AUDIT_LOG", "agent_audit.log"))
RUNBOOK_DIR = Path(os.getenv("RUNBOOK_DIR", "runbooks")).resolve()

REPOS = {
    "DFY-BE": Path("/Users/obakengmokolare/Documents/GitHub/DFY-BE").resolve(),
    "DFY-FE": Path("/Users/obakengmokolare/Documents/GitHub/DFY-FE").resolve(),
}
PROD_REPOS = {"DFY-BE", "DFY-FE"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("it-support-agent")

class GuardrailError(Exception):
    pass

def resolve_repo_path(repo_name: str, relative: str) -> Path:
    if repo_name not in REPOS:
        raise GuardrailError(f"Unknown repo {repo_name!r}")
    root = REPOS[repo_name]
    candidate = (root / relative).resolve()
    if root != candidate and root not in candidate.parents:
        raise GuardrailError(f"Path escapes repo root: {relative!r}")
    return candidate

def run_argv(argv, cwd=None, timeout=120):
    log.info("exec %s (cwd=%s)", argv, cwd)
    return subprocess.run(argv, cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=timeout,
                          shell=False, check=False)

def interactive_approval(repo_name, commit_message):
    print("\n" + "=" * 68)
    print("APPROVAL REQUIRED - production repo push")
    print(f"  repo:    {repo_name}")
    print(f"  message: {commit_message}")
    print(f"  path:    {REPOS[repo_name]}")
    print("=" * 68)
    print("Type 'yes' to approve, anything else to abort: ", end="", flush=True)
    try:
        return input().strip().lower() == "yes"
    except EOFError:
        return False

def audit(event, **fields):
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")

@dataclass
class ToolResult:
    ok: bool
    output: str
    data: dict = field(default_factory=dict)

def tool_scan_repo(repo_name):
    if repo_name not in REPOS:
        return ToolResult(False, f"Unknown repo {repo_name!r}")
    root = REPOS[repo_name]
    if repo_name.startswith("DFY-FE"):
        commands = [["npm", "run", "lint", "--silent"], ["npx", "tsc", "--noEmit"]]
    else:
        commands = [["dotnet", "build", "--nologo", "-v", "quiet"]]
    chunks = []
    for argv in commands:
        try:
            proc = run_argv(argv, cwd=root, timeout=300)
        except FileNotFoundError as exc:
            chunks.append(f"$ {' '.join(argv)}\n[not found: {exc}]"); continue
        except subprocess.TimeoutExpired:
            chunks.append(f"$ {' '.join(argv)}\n[timed out]"); continue
        chunks.append(f"$ {' '.join(argv)}  (exit {proc.returncode})\n" +
                      ((proc.stdout + proc.stderr).strip() or "(no output)"))
    audit("scan_repo", repo=repo_name)
    return ToolResult(True, "\n\n".join(chunks))

def tool_read_file(repo_name, file_relative_path):
    try:
        path = resolve_repo_path(repo_name, file_relative_path)
    except GuardrailError as exc:
        return ToolResult(False, str(exc))
    if not path.is_file():
        return ToolResult(False, f"Not a file: {file_relative_path}")
    if path.stat().st_size > 2_000_000:
        return ToolResult(False, "File too large (>2MB)")
    text = path.read_text(encoding="utf-8", errors="replace")
    audit("read_file", repo=repo_name, path=file_relative_path, bytes=len(text))
    return ToolResult(True, text)

def tool_apply_fix(repo_name, file_relative_path, old_str, new_str):
    try:
        path = resolve_repo_path(repo_name, file_relative_path)
    except GuardrailError as exc:
        return ToolResult(False, str(exc))
    if not path.is_file():
        return ToolResult(False, f"Not a file: {file_relative_path}")
    original = path.read_text(encoding="utf-8")
    n = original.count(old_str)
    if n == 0:
        return ToolResult(False, "old_str not found")
    if n > 1:
        return ToolResult(False, f"old_str appears {n} times; must be unique")
    path.write_text(original.replace(old_str, new_str, 1), encoding="utf-8")
    audit("apply_fix", repo=repo_name, path=file_relative_path)
    return ToolResult(True, f"Applied fix to {file_relative_path}")

def tool_git_commit_and_push(repo_name, commit_message):
    if repo_name not in REPOS:
        return ToolResult(False, f"Unknown repo {repo_name!r}")
    root = REPOS[repo_name]
    if repo_name in PROD_REPOS and not interactive_approval(repo_name, commit_message):
        audit("git_push_aborted", repo=repo_name, message=commit_message)
        return ToolResult(False, "Push aborted by operator")
    if re.search(r"[;&|`$()<>]", commit_message):
        return ToolResult(False, "commit_message contains disallowed characters")
    steps = [["git", "status", "--porcelain"], ["git", "add", "-A"],
             ["git", "commit", "-m", commit_message], ["git", "push"]]
    output = []
    for argv in steps:
        try:
            proc = run_argv(argv, cwd=root, timeout=180)
        except subprocess.TimeoutExpired:
            return ToolResult(False, f"Timed out: {' '.join(argv)}")
        output.append(f"$ {' '.join(argv)}\n{proc.stdout.strip()}{proc.stderr.strip()}")
        if proc.returncode != 0 and argv[1] != "status":
            audit("git_push_failed", repo=repo_name, step=" ".join(argv), rc=proc.returncode)
            return ToolResult(False, "\n\n".join(output))
    audit("git_push_ok", repo=repo_name, message=commit_message)
    return ToolResult(True, "\n\n".join(output))

def tool_get_logs(log_group, since_minutes=60, filter_pattern="ERROR"):
    since_minutes = max(1, min(int(since_minutes), 1440))
    client = boto3.client("logs", region_name=AWS_REGION)
    end = int(datetime.now(timezone.utc).timestamp())
    start = end - since_minutes * 60
    query = (f"fields @timestamp, @message | filter @message like /{filter_pattern}/ "
             f"| sort @timestamp desc | limit 100")
    try:
        started = client.start_query(logGroupName=log_group, startTime=start, endTime=end, queryString=query)
        import time
        qid = started["queryId"]
        for _ in range(30):
            res = client.get_query_results(queryId=qid)
            if res["status"] in ("Complete", "Failed", "Cancelled"):
                break
            time.sleep(1)
        rows = [" | ".join(f.get("value", "") for f in row) for row in res.get("results", [])]
    except ClientError as exc:
        return ToolResult(False, f"CloudWatch error: {exc}")
    audit("get_logs", log_group=log_group, since_minutes=since_minutes)
    return ToolResult(True, "\n".join(rows) or "(no matching log lines)")

def tool_lookup_runbook(query):
    if not RUNBOOK_DIR.is_dir():
        return ToolResult(False, f"No runbooks dir at {RUNBOOK_DIR}")
    terms = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 2}
    scored = []
    for md in RUNBOOK_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        score = sum(lower.count(t) for t in terms)
        if score:
            scored.append((score, md, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return ToolResult(True, "(no matching runbook)")
    joined = "\n\n".join(f"### {p.relative_to(RUNBOOK_DIR)}\n{t}" for _, p, t in scored[:3])
    audit("lookup_runbook", query=query, hits=len(scored[:3]))
    return ToolResult(True, joined)

TOOL_FUNCS = {
    "scan_repo": tool_scan_repo,
    "read_file": tool_read_file,
    "apply_fix": tool_apply_fix,
    "git_commit_and_push": tool_git_commit_and_push,
    "get_logs": tool_get_logs,
    "lookup_runbook": tool_lookup_runbook,
}

TOOL_SPECS = [
    {"toolSpec": {"name": "scan_repo",
        "description": "Run lint/type/build checks for a repo.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "repo_name": {"type": "string", "enum": list(REPOS.keys())}},
            "required": ["repo_name"]}}}},
    {"toolSpec": {"name": "read_file",
        "description": "Read a file inside a repo (path relative to repo root).",
        "inputSchema": {"json": {"type": "object", "properties": {
            "repo_name": {"type": "string", "enum": list(REPOS.keys())},
            "file_relative_path": {"type": "string"}},
            "required": ["repo_name", "file_relative_path"]}}}},
    {"toolSpec": {"name": "apply_fix",
        "description": "Replace an exact unique string in a file.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "repo_name": {"type": "string", "enum": list(REPOS.keys())},
            "file_relative_path": {"type": "string"},
            "old_str": {"type": "string"}, "new_str": {"type": "string"}},
            "required": ["repo_name", "file_relative_path", "old_str", "new_str"]}}}},
    {"toolSpec": {"name": "git_commit_and_push",
        "description": "Commit all changes and push. Prod repos require approval.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "repo_name": {"type": "string", "enum": list(REPOS.keys())},
            "commit_message": {"type": "string"}},
            "required": ["repo_name", "commit_message"]}}}},
    {"toolSpec": {"name": "get_logs",
        "description": "Query CloudWatch Logs Insights.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "log_group": {"type": "string"},
            "since_minutes": {"type": "integer", "minimum": 1, "maximum": 1440},
            "filter_pattern": {"type": "string"}},
            "required": ["log_group"]}}}},
    {"toolSpec": {"name": "lookup_runbook",
        "description": "Search local runbook markdown files.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}}},
]

SYSTEM_PROMPT = """You are an expert IT Support Engineer who owns the IT support lane end-to-end.

Responsibilities:
- Triage issues (infra, access, CI/CD, networking, tooling, code bugs)
- Diagnose using logs, runbooks, and source code
- Apply minimal targeted fixes
- Verify the fix (re-scan after editing)
- Only then commit and push

Code workflow (mandatory order):
1. scan_repo(repo_name)
2. read_file(repo_name, path)
3. apply_fix(repo_name, path, old_str, new_str)
4. scan_repo(repo_name) again to confirm the error is gone
5. git_commit_and_push(repo_name, message) only if clean
6. Summarize what you found, changed, and the result

Rules:
- lookup_runbook first if the issue looks like a known pattern
- Never guess - diagnose from evidence
- Production repos require human approval before push
- Never commit broken code

Tone: concise, technical, developer-friendly. No fluff.
"""

def bedrock_client():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)

def dispatch_tool(name, args):
    fn = TOOL_FUNCS.get(name)
    if not fn:
        return ToolResult(False, f"Unknown tool {name!r}")
    try:
        return fn(**args)
    except TypeError as exc:
        return ToolResult(False, f"Bad arguments for {name}: {exc}")
    except Exception as exc:
        log.exception("Tool %s crashed", name)
        return ToolResult(False, f"Tool {name} crashed: {exc}")

def run_agent(user_message):
    client = bedrock_client()
    messages = [{"role": "user", "content": [{"text": user_message}]}]
    for _ in range(MAX_TURNS):
        resp = client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig={"tools": TOOL_SPECS},
            inferenceConfig={"maxTokens": 2048, "temperature": 0.2},
        )
        out_msg = resp["output"]["message"]
        messages.append(out_msg)
        if resp.get("stopReason") != "tool_use":
            return "".join(b.get("text", "") for b in out_msg.get("content", [])).strip() or "(no response)"
        tool_results = []
        for block in out_msg["content"]:
            if "toolUse" not in block:
                continue
            tu = block["toolUse"]
            log.info("Tool call: %s %s", tu["name"], json.dumps(tu["input"])[:200])
            result = dispatch_tool(tu["name"], tu["input"])
            tool_results.append({"toolResult": {
                "toolUseId": tu["toolUseId"],
                "content": [{"text": result.output[:20_000]}],
                "status": "success" if result.ok else "error"}})
        messages.append({"role": "user", "content": tool_results})
    return "Agent exceeded max turns."

def main():
    if len(sys.argv) < 2:
        print('Usage: python agent.py "your request"'); return 2
    request = " ".join(sys.argv[1:])
    print(f"\n>>> {request}\n")
    try:
        print(run_agent(request))
    except ClientError as exc:
        print(f"AWS error: {exc}"); return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
