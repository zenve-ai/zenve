import json

import httpx

from zenve_db.models import Project
from zenve_models.errors import NotFoundError, ValidationError
from zenve_models.repo import AgentDetail, AgentSummary, RunDetail, RunSummary
from zenve_services.repo_writer import validate_relpath
from zenve_utils.github import get_repo_file, list_repo_dir, list_tree_paths


class RepoReaderService:
    def require_github(self, project: Project) -> tuple[int, str, str]:
        if (
            not project.github_installation_id
            or not project.github_repo
            or not project.github_default_branch
        ):
            raise ValidationError("Project has no GitHub repo connected")
        return project.github_installation_id, project.github_repo, project.github_default_branch

    def list_agents(self, project: Project) -> list[AgentSummary]:
        installation_id, repo, branch = self.require_github(project)
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

    def get_agent(self, project: Project, name: str) -> AgentDetail:
        installation_id, repo, branch = self.require_github(project)
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
        files = self.list_agent_files(project, name)
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

    def read_agent_file(self, project: Project, name: str, relpath: str) -> bytes:
        installation_id, repo, branch = self.require_github(project)
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

    def list_agent_files(self, project: Project, name: str) -> list[str]:
        installation_id, repo, branch = self.require_github(project)
        prefix = f".zenve/agents/{name}/"
        paths = list_tree_paths(
            installation_id,
            repo,
            prefix,
            ref=branch,
        )
        return [p[len(prefix) :] for p in paths]

    def list_runs(self, project: Project, name: str) -> list[RunSummary]:
        installation_id, repo, branch = self.require_github(project)
        entries = list_repo_dir(
            installation_id,
            repo,
            f".zenve/agents/{name}/runs",
            ref=branch,
        )
        return [
            RunSummary(run_id=e["name"].removesuffix(".json"))
            for e in entries
            if e.get("type") == "file" and e["name"].endswith(".json")
        ]

    def get_run(self, project: Project, name: str, run_id: str) -> RunDetail:
        installation_id, repo, branch = self.require_github(project)
        try:
            run_bytes = get_repo_file(
                installation_id,
                repo,
                f".zenve/agents/{name}/runs/{run_id}.json",
                ref=branch,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise NotFoundError(f"Run '{run_id}' not found") from exc
            raise
        data = json.loads(run_bytes)
        return RunDetail(
            run_id=run_id,
            status=data.get("status"),
            started_at=data.get("started_at"),
            data=data,
        )

    def get_project_settings(self, project: Project) -> dict:
        installation_id, repo, branch = self.require_github(project)
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
