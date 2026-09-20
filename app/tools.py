from __future__ import annotations
import re, subprocess
from pathlib import Path
from typing import Iterable

class ToolError(Exception): pass

class Tools:
    def __init__(self,audit,timeout=120): self.audit,self.timeout=audit,timeout
    @staticmethod
    def safe_path(root:Path,relative:str)->Path:
        candidate=(root/relative).resolve()
        if candidate!=root and root not in candidate.parents: raise ToolError("Path escapes repository root")
        return candidate
    def list_files(self,root:Path,limit=200):
        ignored={".git","node_modules","bin","obj","dist","build",".venv","venv"}; out=[]
        for p in root.rglob("*"):
            if p.is_file() and not any(x in ignored for x in p.parts):
                out.append(str(p.relative_to(root)))
                if len(out)>=limit: break
        return sorted(out)
    def read_file(self,root,relative):
        p=self.safe_path(root,relative)
        if not p.is_file(): raise ToolError(f"Not a file: {relative}")
        if p.stat().st_size>2_000_000: raise ToolError("File exceeds 2MB safety limit")
        self.audit.write("read_file",path=relative); return p.read_text(encoding="utf-8",errors="replace")
    def search(self,root,pattern,limit=50):
        rx=re.compile(pattern,re.I); hits=[]
        for rel in self.list_files(root,1000):
            try: lines=(root/rel).read_text(encoding="utf-8",errors="replace").splitlines()
            except OSError: continue
            for n,line in enumerate(lines,1):
                if rx.search(line):
                    hits.append({"file":rel,"line":n,"text":line[:500]})
                    if len(hits)>=limit:return hits
        return hits
    def apply_fix(self,root,relative,old,new):
        p=self.safe_path(root,relative)
        if not p.is_file(): raise ToolError(f"Not a file: {relative}")
        text=p.read_text(encoding="utf-8"); count=text.count(old)
        if count!=1: raise ToolError(f"Expected exactly one match, found {count}")
        p.write_text(text.replace(old,new,1),encoding="utf-8"); self.audit.write("apply_fix",path=relative)
        return True
    def run(self,argv:Iterable[str],cwd:Path,timeout=None):
        argv=list(argv)
        if not argv or any("\x00" in x for x in argv): raise ToolError("Invalid command")
        p=subprocess.run(argv,cwd=str(cwd),capture_output=True,text=True,shell=False,timeout=timeout or self.timeout)
        out=(p.stdout+"\n"+p.stderr).strip(); self.audit.write("command",argv=argv,cwd=str(cwd),returncode=p.returncode)
        if p.returncode!=0: raise ToolError(f"Command failed ({p.returncode}): {out[-4000:]}")
        return out[-12000:]
    def verify(self,root):
        if (root/"pyproject.toml").exists() or (root/"requirements.txt").exists(): return self.run(["python","-m","compileall","-q","."],root)
        if any(root.glob("*.csproj")) or any(root.glob("*.sln")): return self.run(["dotnet","build","--nologo","-v","quiet"],root)
        if (root/"package.json").exists(): return self.run(["npm","run","build","--if-present"],root)
        return "No standard build manifest detected; static verification only."
