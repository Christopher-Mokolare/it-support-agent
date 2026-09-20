from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os, re, yaml

@dataclass(frozen=True)
class Project:
    name: str
    description: str = ""
    repos: dict[str, str] = field(default_factory=dict)
    environments: dict[str, dict] = field(default_factory=dict)
    production: bool = True
    def repo_path(self, repo: str) -> Path:
        if repo not in self.repos: raise KeyError(f"Unknown repo {repo!r} for project {self.name!r}")
        raw=self.repos[repo]
        def repl(m): return os.getenv(m.group(1),m.group(2) or "")
        raw=re.sub(r"\\$\\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\\}",repl,raw)
        return Path(os.path.expanduser(os.path.expandvars(raw))).resolve()

class ProjectRegistry:
    def __init__(self,path:Path):
        self.path=path
        raw=yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {"projects":{}}
        self.projects={name:Project(name=name,**(value or {})) for name,value in (raw.get("projects") or {}).items()}
    def get(self,name:str)->Project:
        for key,p in self.projects.items():
            if key.lower()==name.lower(): return p
        raise KeyError(f"Unknown project {name!r}. Available: {', '.join(self.projects)}")
    def all(self)->list[Project]: return list(self.projects.values())
    def resolve(self,project:str|None,repo:str|None=None):
        if project:
            p=self.get(project)
            return p,repo
        if repo:
            matches=[(p,repo) for p in self.projects.values() if repo in p.repos]
            if len(matches)==1:return matches[0]
        raise KeyError("Project context is required. Specify project=<name> or configure an unambiguous repo.")
