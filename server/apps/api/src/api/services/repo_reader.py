import json

import httpx

from api.db.models import Workspace
from api.models.errors import NotFoundError, ValidationError
from api.models.repo import AgentDetail, AgentSummary
from api.services.repo_writer import validate_relpath
from api.utils.github import get_repo_file, list_repo_dir, list_tree_paths


class RepoReaderService:
    def require_github(self, workspace: Workspace) -> tuple[int, str, str]:
        if (
            not workspace.github_installation_id
            or not workspace.github_repo
            or not workspace.github_default_branch
        ):
            raise ValidationError("Workspace has no GitHub repo connected")
        return workspace.github_installation_id, workspace.github_repo, workspace.github_default_branch

    def list_agents(self, workspace: Workspace) -> list[AgentSummary]:
        installation_id, repo, branch = self.require_github(workspace)
        entries = list_repo_dir(
            installation_id,
            repo,
            ".zenve/agents",
            ref=branch,
        )
        agents = []
        for entry in entries:
            if entry.get("type") != "dir":
                continue
            slug = entry["name"]
            try:
                settings_bytes = get_repo_file(
                    installation_id,
                    repo,
                    f".zenve/agents/{slug}/settings.json",
                    ref=branch,
                )
                settings = json.loads(settings_bytes)
                agents.append(
                    AgentSummary(
                        name=settings.get("name", slug),
                        slug=slug,
                        adapter_type=settings.get("adapter_type", ""),
                        enabled=settings.get("enabled", True),
                    )
                )
            except Exception:
                continue
        return agents

    def get_agent(self, workspace: Workspace, name: str) -> AgentDetail:
        installation_id, repo, branch = self.require_github(workspace)
        try:
            settings_bytes = get_repo_file(
                installation_id,
                repo,
                f".zenve/agents/{name}/settings.json",
                ref=branch,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundError(f"Agent '{name}' not found") from exc
            raise
        settings = json.loads(settings_bytes)
        files = self.list_agent_files(workspace, name)
        return AgentDetail(
            name=settings.get("name", name),
            slug=name,
            adapter_type=settings.get("adapter_type", ""),
            enabled=settings.get("enabled", True),
            adapter_config=settings.get("adapter_config", {}),
            skills=settings.get("skills", []),
            tools=settings.get("tools", []),
            heartbeat_interval_seconds=settings.get("heartbeat_interval_seconds", 0),
            has_soul="SOUL.md" in files,
            has_agents="AGENTS.md" in files,
            has_heartbeat="HEARTBEAT.md" in files,
            files=files,
        )

    def read_agent_file(self, workspace: Workspace, name: str, relpath: str) -> bytes:
        installation_id, repo, branch = self.require_github(workspace)
        validate_relpath(relpath)
        try:
            return get_repo_file(
                installation_id,
                repo,
                f".zenve/agents/{name}/{relpath}",
                ref=branch,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundError(f"File '{relpath}' not found") from exc
            raise

    def list_agent_files(self, workspace: Workspace, name: str) -> list[str]:
        installation_id, repo, branch = self.require_github(workspace)
        prefix = f".zenve/agents/{name}/"
        paths = list_tree_paths(
            installation_id,
            repo,
            prefix,
            ref=branch,
        )
        return [p[len(prefix):] for p in paths]

    def get_workspace_settings(self, workspace: Workspace) -> dict:
        installation_id, repo, branch = self.require_github(workspace)
        try:
            settings_bytes = get_repo_file(
                installation_id,
                repo,
                ".zenve/settings.json",
                ref=branch,
            )
            return json.loads(settings_bytes)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {}
            raise
