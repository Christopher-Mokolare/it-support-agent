from __future__ import annotations
import json,re
from .audit import AuditLog
from .projects import ProjectRegistry
from .provider import create_provider
from .tools import Tools,ToolError
from .config import settings

SYSTEM="""You are a production IT/DevOps support engineer. You support multiple projects.
Always establish project context before touching a repository. Diagnose from evidence, not guesses.
Use read/search/inspection first. Never expose secrets. Never execute arbitrary shell commands.
Changes must be minimal and verified. Production writes, deployments, destructive operations and git pushes require explicit human approval.
If evidence is insufficient, say what is missing. At the end report project, evidence, root cause, changes, verification and remaining risks."""

TOOL_DEFS=[
 {"type":"function","function":{"name":"list_projects","description":"List configured projects.","parameters":{"type":"object","properties":{}}}},
 {"type":"function","function":{"name":"list_files","description":"List files in a project's repository.","parameters":{"type":"object","properties":{"project":{"type":"string"},"repo":{"type":"string"}},"required":["project","repo"]}}},
 {"type":"function","function":{"name":"read_file","description":"Read a repository file.","parameters":{"type":"object","properties":{"project":{"type":"string"},"repo":{"type":"string"},"path":{"type":"string"}},"required":["project","repo","path"]}}},
 {"type":"function","function":{"name":"search_code","description":"Search repository text with a regex.","parameters":{"type":"object","properties":{"project":{"type":"string"},"repo":{"type":"string"},"pattern":{"type":"string"}},"required":["project","repo","pattern"]}}},
 {"type":"function","function":{"name":"apply_fix","description":"Apply one exact unique text replacement. Does not commit or push.","parameters":{"type":"object","properties":{"project":{"type":"string"},"repo":{"type":"string"},"path":{"type":"string"},"old":{"type":"string"},"new":{"type":"string"}},"required":["project","repo","path","old","new"]}}},
 {"type":"function","function":{"name":"verify","description":"Run the repository's standard verification command.","parameters":{"type":"object","properties":{"project":{"type":"string"},"repo":{"type":"string"}},"required":["project","repo"]}}}
]

class Agent:
    def __init__(self, registry=None, provider=None):
        self.registry=registry or ProjectRegistry(settings.projects_file)
        self.audit=AuditLog(settings.audit_log)
        self.tools=Tools(self.audit,settings.command_timeout)
        self.provider=provider or create_provider(settings)

    def dispatch(self,name,args):
        if name=="list_projects": return [{"name":p.name,"description":p.description,"repos":list(p.repos)} for p in self.registry.all()]
        p,r=self.registry.resolve(args.get("project"),args.get("repo")); root=p.repo_path(r)
        if not root.exists(): raise ToolError(f"Configured repo path does not exist: {root}")
        if name=="list_files": return self.tools.list_files(root)
        if name=="read_file": return self.tools.read_file(root,args["path"])
        if name=="search_code": return self.tools.search(root,args["pattern"])
        if name=="apply_fix": return {"changed":True,"path":args["path"]} if not self.tools.apply_fix(root,args["path"],args["old"],args["new"]) else None
        if name=="verify": return self.tools.verify(root)
        raise ToolError(f"Unknown tool {name}")

    def run(self, request: str) -> str:
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":request}]
        for _ in range(settings.max_turns):
            response=self.provider.complete(messages,TOOL_DEFS)
            choice=response["choices"][0]["message"]
            messages.append(choice)
            calls=choice.get("tool_calls") or []
            if not calls: return choice.get("content") or "No response."
            for call in calls:
                name=call["function"]["name"]
                args=json.loads(call["function"].get("arguments") or "{}")
                try: result=self.dispatch(name,args)
                except Exception as e: result={"error":str(e)}
                self.audit.write("tool_result",tool=name,ok="error" not in result if isinstance(result,dict) else True)
                messages.append({"role":"tool","tool_call_id":call["id"],"name":name,"content":json.dumps(result,default=str)})
        return "Maximum reasoning turns reached; no final answer was produced."
