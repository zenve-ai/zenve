from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from runtime.models.errors import ConflictError, ExternalError, NotFoundError, ValidationError
from runtime.models.run import AgentStats, WorkspaceRunDetail
from runtime.models.workspace import AgentSummary, ScaffoldWorkspaceBody, Workspace, WorkspaceCreate, WorkspaceDetail


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
            "workspaces": [w.model_dump(exclude={"agent_count"}) for w in self.workspaces],
        }
        tmp = self.registry_path.with_suffix(self.registry_path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.registry_path)

    def list(self) -> list[Workspace]:
        return [w.model_copy(update={"agent_count": self.count_agents(w.path)}) for w in self.workspaces]

    def count_agents(self, workspace_path: str) -> int:
        agents_dir = Path(workspace_path) / ZENVE_DIR / AGENTS_SUBDIR
        if not agents_dir.exists():
            return 0
        return sum(1 for p in agents_dir.iterdir() if p.is_dir())

    def list_agents(self, workspace_id: str) -> list[AgentSummary]:
        workspace = self.get(workspace_id)
        agents_dir = Path(workspace.path) / ZENVE_DIR / AGENTS_SUBDIR
        if not agents_dir.exists():
            return []
        results: list[AgentSummary] = []
        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            slug = agent_dir.name
            settings_path = agent_dir / SETTINGS_FILE
            name = slug
            adapter_type = ""
            model = ""
            skills: list[str] = []
            tools: list[str] = []
            enabled = True
            if settings_path.exists():
                with settings_path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                name = data.get("name", slug)
                adapter_type = data.get("adapter_type", "")
                model = data.get("adapter_config", {}).get("model", "")
                skills = data.get("skills", [])
                tools = data.get("tools", [])
                enabled = data.get("enabled", True)
                mode = data.get("mode", "")
            results.append(AgentSummary(
                slug=slug,
                name=name,
                adapter_type=adapter_type,
                model=model,
                skills=skills,
                tools=tools,
                enabled=enabled,
                mode=mode,
            ))
        return results

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

    def get_agent_stats(self, workspace_id: str, agent_slug: str) -> AgentStats:
        workspace = self.get(workspace_id)
        runs_dir = Path(workspace.path) / ZENVE_DIR / AGENTS_SUBDIR / agent_slug / "runs"
        runs: list[WorkspaceRunDetail] = []
        if runs_dir.exists():
            for path in sorted(runs_dir.glob("*.json"), key=lambda p: p.stem, reverse=True):
                try:
                    with path.open("r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    runs.append(WorkspaceRunDetail.model_validate(data))
                except Exception:
                    pass
        completed = sum(1 for r in runs if r.status == "completed")
        failed = sum(1 for r in runs if r.status == "failed")
        return AgentStats(
            agent=agent_slug,
            total_runs=len(runs),
            completed_runs=completed,
            failed_runs=failed,
            runs=runs,
        )

    def scaffold(self, body: ScaffoldWorkspaceBody, template_svc: object) -> Workspace:
        from runtime.services.template_service import TemplateService
        svc: TemplateService = template_svc  # type: ignore[assignment]

        path = Path(body.path).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise ValidationError(f"Path does not exist or is not a directory: {path}")

        zenve_dir = path / ZENVE_DIR
        agents_dir = zenve_dir / AGENTS_SUBDIR
        zenve_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower().strip()).strip("-") or "project"
        pipeline: dict[str, None] = {}

        for template_id in body.agents:
            template = svc.get_template(template_id)
            agent_slug = template.slug or template_id
            try:
                tfiles = svc.get_template_files(template_id)
                raw_files = {k: base64.b64decode(v) for k, v in tfiles.files.items()}
            except Exception:
                raw_files = {}
            agent_settings = {
                "slug": agent_slug,
                "name": template.name,
                "adapter_type": template.adapter_type,
                "adapter_config": template.adapter_config,
                "skills": template.skills,
                "tools": template.tools,
                "heartbeat_interval_seconds": template.heartbeat_interval_seconds,
                "github_label": f"zenve:{agent_slug}",
                "enabled": True,
                "mode": template.mode,
            }
            raw_files["settings.json"] = json.dumps(agent_settings, indent=2).encode()
            agent_out = agents_dir / agent_slug
            for relpath, content in raw_files.items():
                dest = agent_out / relpath
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
            pipeline[f"zenve:{agent_slug}"] = None

        for skill_id in body.skills:
            try:
                skill_files = svc.get_skill_files(skill_id)
            except Exception:
                continue
            skill_out = path / ".agents" / "skills" / skill_id
            skill_out.mkdir(parents=True, exist_ok=True)
            for relpath, content in skill_files.files.items():
                dest = skill_out / relpath
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(base64.b64decode(content))
            link_dir = path / ".claude" / "skills"
            link_dir.mkdir(parents=True, exist_ok=True)
            link_path = link_dir / skill_id
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()
            link_path.symlink_to(Path("../../.agents/skills") / skill_id)

        root_settings = {
            "project": slug,
            "description": body.description,
            "default_branch": body.default_branch,
            "commit_message_prefix": "[zenve]",
            "run_timeout_seconds": 600,
            "stack": body.stack,
            "pipeline": pipeline,
        }
        (zenve_dir / SETTINGS_FILE).write_text(json.dumps(root_settings, indent=2), encoding="utf-8")

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
