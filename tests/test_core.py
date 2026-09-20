import os
from pathlib import Path
from app.projects import ProjectRegistry
from app.tools import Tools,ToolError
from app.audit import AuditLog

def test_path_confinement(tmp_path):
    root=tmp_path/"repo"; root.mkdir(); (root/"a.txt").write_text("ok")
    assert Tools.safe_path(root,"a.txt")==root/"a.txt"
    try: Tools.safe_path(root,"../secret")
    except ToolError: pass
    else: raise AssertionError("path traversal was not blocked")

def test_unique_fix(tmp_path):
    root=tmp_path/"repo"; root.mkdir(); (root/"a.txt").write_text("x")
    t=Tools(AuditLog(tmp_path/"audit.jsonl"))
    t.apply_fix(root,"a.txt","x","y")
    assert (root/"a.txt").read_text()=="y"

def test_registry(tmp_path):
    p=tmp_path/"projects.yaml"
    p.write_text("projects:\n  Demo:\n    repos:\n      app: ~/demo\n")
    r=ProjectRegistry(p)
    assert r.get("demo").name=="Demo"
