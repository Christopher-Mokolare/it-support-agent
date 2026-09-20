from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable

class ToolError(Exception):
    pass

class Tools:
    def __init__(self, audit, timeout=120):
        self.audit = audit
        self.timeout = timeout

    @staticmethod
    def safe_path(root: Path, relative: str) -> Path:
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            raise ToolError("Path escapes the repository root")
        return candidate

    def read_file(self, root: Path, relative: str) -> str:
        path = self.safe_path(root, relative)
        if not path.is_file():
            raise ToolError(f"Not a file: {relative}")
        if path.stat().st_size > 2_000_000:
            raise ToolError("File exceeds 2MB safety limit")
        self.audit.write("read_file", path=relative)
        return path.read_text(encoding="utf-8", errors="replace")

    def list_files(self, root: Path, limit=200) -> list[str]:
        ignored={".git","node_modules","bin","obj","dist","build",".venv","venv"}
        files=[]
        for p in root.rglob("*"):
            if p.is_file() and not any(part in ignored for part in p.parts):
                files.append(str(p.relative_to(root)))
                if len(files)>=limit: break
        return sorted(files)

    def search(self, root: Path, pattern: str, limit=50) -> list[dict]:
        rx=re.compile(pattern, re.IGNORECASE)
        hits=[]
        for rel in self.list_files(root, 1000):
            p=root/rel
            try: text=p.read_text(encoding="utf-8",errors="replace")
            except OSError: continue
            for n,line in enumerate(text.splitlines(),1):
                if rx.search(line):
                    hits.append({"file":rel,"line":n,"text":line[:500]})
                    if len(hits)>=limit: return hits
        return hits

    def apply_fix(self, root: Path, relative: str, old: str, new: str):
        path=self.safe_path(root,relative)
        if not path.is_file(): raise ToolError(f"Not a file: {relative}")
        original=path.read_text(encoding="utf-8")
        count=original.count(old)
        if count != 1: raise ToolError(f"Expected exactly one match, found {count}")
        path.write_text(original.replace(old,new,1),encoding="utf-8")
        self.audit.write("apply_fix",path=relative)

    def run(self, argv: Iterable[str], cwd: Path, timeout=None) -> str:
        argv=list(argv)
        if not argv or any("\x00" in x for x in argv): raise ToolError("Invalid command")
        proc=subprocess.run(argv,cwd=str(cwd),capture_output=True,text=True,shell=False,
                           timeout=timeout or self.timeout,check=False)
        output=(proc.stdout+"\n"+proc.stderr).strip()
        self.audit.write("command",argv=argv,cwd=str(cwd),returncode=proc.returncode)
        if proc.returncode != 0:
            raise ToolError(f"Command failed ({proc.returncode}): {output[-4000:]}")
        return output[-12000:]

    def verify(self, root: Path) -> str:
        if (root/"pyproject.toml").exists() or (root/"requirements.txt").exists():
            return self.run(["python","-m","compileall","-q","."],root)
        if (root/"*.csproj").exists():
            return self.run(["dotnet","build","--nologo","-v","quiet"],root)
        if (root/"package.json").exists():
            return self.run(["npm","run","build","--if-present"],root)
        return "No standard build manifest detected; static verification only."
