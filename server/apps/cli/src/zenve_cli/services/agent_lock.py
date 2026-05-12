from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

LOCK_FILENAME = "agents-lock.json"
LOCK_VERSION = 1

# Files excluded from hashing — user-tunable, never tracked for drift.
EXCLUDED_FILES: frozenset[str] = frozenset({"settings.json"})

# Subdirs created at runtime — never part of the template.
RUNTIME_DIRS: tuple[str, ...] = ("runs/", "memory/")

AgentStatus = Literal["clean", "modified", "unknown", "missing"]


def normalize(content: bytes) -> bytes:
    return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def hash_content(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(normalize(content)).hexdigest()


def hash_template_files(files: dict[str, bytes]) -> dict[str, str]:
    """Hash the in-memory template files (settings.json excluded)."""
    return {
        path: hash_content(content)
        for path, content in sorted(files.items())
        if path not in EXCLUDED_FILES
    }


def is_runtime_path(rel: str) -> bool:
    return any(rel.startswith(d) for d in RUNTIME_DIRS)


class AgentLockService:
    """Manages .zenve/agents/agents-lock.json — tracks per-agent file hashes
    so `zenve agent update` can tell which agents are pristine vs. user-modified."""

    def __init__(self, zdir: Path) -> None:
        self.zdir = zdir
        self.path = zdir / "agents" / LOCK_FILENAME

    def load(self) -> dict:
        if not self.path.exists():
            return {"version": LOCK_VERSION, "agents": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"version": LOCK_VERSION, "agents": {}}
        if not isinstance(data, dict) or "agents" not in data:
            return {"version": LOCK_VERSION, "agents": {}}
        return data

    def save(self, lock: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(lock, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def record_install(
        self,
        slug: str,
        template_id: str,
        files: dict[str, bytes],
        source: str,
        commit_sha: str | None,
    ) -> None:
        lock = self.load()
        agents = lock.setdefault("agents", {})
        agents[slug] = {
            "template": template_id,
            "source": source,
            "sourceCommitSha": commit_sha,
            "installedAt": datetime.now(UTC)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "files": hash_template_files(files),
        }
        self.save(lock)

    def remove(self, slug: str) -> None:
        lock = self.load()
        agents = lock.get("agents", {})
        if slug in agents:
            del agents[slug]
            self.save(lock)

    def get_entry(self, slug: str) -> dict | None:
        return self.load().get("agents", {}).get(slug)

    def hash_installed(self, slug: str) -> dict[str, str] | None:
        agent_dir = self.zdir / "agents" / slug
        if not agent_dir.exists():
            return None
        result: dict[str, str] = {}
        for p in agent_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(agent_dir).as_posix()
            if rel in EXCLUDED_FILES or is_runtime_path(rel):
                continue
            result[rel] = hash_content(p.read_bytes())
        return result

    def status(self, slug: str) -> AgentStatus:
        current = self.hash_installed(slug)
        if current is None:
            return "missing"
        entry = self.get_entry(slug)
        if not entry:
            return "unknown"
        return "clean" if current == entry.get("files", {}) else "modified"
