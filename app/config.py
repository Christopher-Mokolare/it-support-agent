from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "groq")
    model: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    api_key: str | None = os.getenv("LLM_API_KEY")
    base_url: str = os.getenv("LLM_BASE_URL", "")
    max_turns: int = int(os.getenv("AGENT_MAX_TURNS", "12"))
    command_timeout: int = int(os.getenv("AGENT_COMMAND_TIMEOUT", "120"))
    audit_log: Path = Path(os.getenv("AGENT_AUDIT_LOG", str(ROOT / "data" / "audit.jsonl")))
    projects_file: Path = Path(os.getenv("PROJECTS_FILE", str(ROOT / "config" / "projects.yaml")))

settings = Settings()
