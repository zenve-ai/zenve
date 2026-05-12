from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from runtime.models.errors import ConflictError, ExternalError, NotFoundError, ValidationError
from runtime.models.workspace import Workspace, WorkspaceCreate, WorkspaceDetail


def git_remote_slug(repo_root: Path) -> str | None:
    """Return `owner/repo` from the git remote origin URL, or None."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
        )
        url = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}"


ZENVE_DIR = ".zenve"
SETTINGS_FILE = "settings.json"
AGENTS_SUBDIR = "agents"
REGISTRY_VERSION = 1


def default_registry_path() -> Path:
    return Path.home() / ".zenve" / "workspaces.json"


class WorkspaceService:
    """Filesystem-backed registry of zenve workspaces (local repos with `.zenve/`)."""

    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or default_registry_path()
        self.lock = threading.Lock()
        self.workspaces: list[Workspace] = []
        self.load()

    def load(self) -> None:
        if not self.registry_path.exists():
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            self.workspaces = []
            self.save()
            return
        with self.registry_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.workspaces = [Workspace.model_validate(w) for w in data.get("workspaces", [])]

    def save(self) -> None:
        payload = {
            "version": REGISTRY_VERSION,
            "workspaces": [w.model_dump() for w in self.workspaces],
        }
        tmp = self.registry_path.with_suffix(self.registry_path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.registry_path)

    def list(self) -> list[Workspace]:
        return list(self.workspaces)

    def get(self, workspace_id: str) -> Workspace:
        for w in self.workspaces:
            if w.id == workspace_id:
                return w
        raise NotFoundError(f"Workspace {workspace_id} not found")

    def resolve_path(self, workspace_id: str) -> Path:
        return Path(self.get(workspace_id).path)

    def register(self, body: WorkspaceCreate) -> Workspace:
        path = Path(body.path).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise ValidationError(f"Path does not exist or is not a directory: {path}")
        zenve_path = path / ZENVE_DIR
        if not zenve_path.exists():
            raise ValidationError(
                f"No {ZENVE_DIR}/ at {path}. Run `zenve init` here first, or point at a different repo."
            )
        settings_path = zenve_path / SETTINGS_FILE
        if not settings_path.exists():
            raise ValidationError(
                f"{ZENVE_DIR}/ exists at {path} but is missing {SETTINGS_FILE} — re-run `zenve init`."
            )

        with self.lock:
            for w in self.workspaces:
                if w.path == str(path):
                    raise ConflictError(f"Workspace already registered at {path}")
            workspace = Workspace(
                id=uuid.uuid4().hex[:12],
                path=str(path),
                registered_at=datetime.now(UTC).isoformat(),
            )
            self.workspaces.append(workspace)
            self.save()
        return workspace

    def unregister(self, workspace_id: str) -> None:
        with self.lock:
            for i, w in enumerate(self.workspaces):
                if w.id == workspace_id:
                    del self.workspaces[i]
                    self.save()
                    return
            raise NotFoundError(f"Workspace {workspace_id} not found")

    def detail(self, workspace_id: str) -> WorkspaceDetail:
        workspace = self.get(workspace_id)
        path = Path(workspace.path)
        if not path.exists():
            raise ExternalError(f"Workspace path no longer exists on disk: {path}")
        settings_path = path / ZENVE_DIR / SETTINGS_FILE
        if not settings_path.exists():
            raise ExternalError(f"Missing {ZENVE_DIR}/{SETTINGS_FILE} at {path}")
        with settings_path.open("r", encoding="utf-8") as fh:
            settings = json.load(fh)

        agents_dir = path / ZENVE_DIR / AGENTS_SUBDIR
        agent_slugs: list[str] = []
        if agents_dir.exists():
            agent_slugs = sorted(p.name for p in agents_dir.iterdir() if p.is_dir())

        return WorkspaceDetail(
            id=workspace.id,
            path=workspace.path,
            registered_at=workspace.registered_at,
            project=settings.get("project", path.name),
            description=settings.get("description", ""),
            default_branch=settings.get("default_branch", "main"),
            run_schedule=settings.get("run_schedule"),
            pipeline=settings.get("pipeline", {}),
            stack=settings.get("stack", []),
            agents=agent_slugs,
            repo=git_remote_slug(path),
        )
