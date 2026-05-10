import time
from pathlib import Path

import httpx
import yaml

from api.config import Settings
from api.models.errors import (
    ConflictError,
    ExternalError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from api.models.github_template import GitHubTemplateSummary, SkillSummary

GITHUB_API = "https://api.github.com"

_cache: dict[str, tuple[object, float]] = {}
CACHE_TTL = 300.0


class GitHubTemplateService:
    def __init__(self, settings: Settings, base_path: str = "") -> None:
        self.repo = settings.github_agents_repo
        self.token = settings.github_token
        self.base_path = base_path.strip("/")

    def full_path(self, path: str) -> str:
        path = path.strip("/")
        if not self.base_path:
            return path
        return f"{self.base_path}/{path}" if path else self.base_path

    def full_prefix(self, prefix: str) -> str:
        if not self.base_path:
            return prefix
        return f"{self.base_path}/{prefix}"

    def is_enabled(self) -> bool:
        return bool(self.repo)

    def auth_headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def cached_get(self, url: str, params: dict | None = None) -> object:
        cache_key = url + str(sorted((params or {}).items()))
        now = time.monotonic()
        if cache_key in _cache:
            data, expires_at = _cache[cache_key]
            if now < expires_at:
                return data
        try:
            response = httpx.get(url, headers=self.auth_headers(), params=params, timeout=15)
        except httpx.RequestError as exc:
            raise ExternalError("GitHub API unreachable") from exc
        if response.status_code == 404:
            raise NotFoundError(f"Not found in GitHub repo: {url}")
        if response.status_code in (401, 403):
            raise ValidationError(f"Cannot access GitHub repo (HTTP {response.status_code}): {url}")
        if response.status_code == 429:
            raise RateLimitError("GitHub API rate limit exceeded")
        if not response.is_success:
            raise ExternalError(f"GitHub API error (HTTP {response.status_code}): {url}")
        data = response.json()
        _cache[cache_key] = (data, now + CACHE_TTL)
        return data

    def list_repo_dir(self, path: str) -> list[dict]:
        url = f"{GITHUB_API}/repos/{self.repo}/contents/{self.full_path(path)}"
        result = self.cached_get(url)
        if not isinstance(result, list):
            raise NotFoundError(f"Path '{path}' is not a directory")
        return result

    def get_head_sha(self) -> str | None:
        """Return the HEAD commit SHA of the registry's default branch (main, then master)."""
        for branch in ("main", "master"):
            try:
                ref_data = self.cached_get(
                    f"{GITHUB_API}/repos/{self.repo}/git/ref/heads/{branch}"
                )
            except NotFoundError:
                continue
            try:
                return ref_data["object"]["sha"]  # type: ignore[index]
            except (KeyError, TypeError):
                return None
        return None

    def list_tree_blobs(self, prefix: str) -> list[dict]:
        tree_sha = self.get_head_sha()
        if tree_sha is None:
            raise NotFoundError(f"No default branch found in repo {self.repo}")
        tree_url = f"{GITHUB_API}/repos/{self.repo}/git/trees/{tree_sha}"
        tree_data = self.cached_get(tree_url, params={"recursive": "1"})
        tree = tree_data["tree"]  # type: ignore[index]
        full = self.full_prefix(prefix)
        return [
            item
            for item in tree
            if item.get("type") == "blob" and item.get("path", "").startswith(full)
        ]

    def fetch_blob_bytes(self, blob_url: str) -> bytes:
        try:
            response = httpx.get(
                blob_url,
                headers={**self.auth_headers(), "Accept": "application/vnd.github.raw+json"},
                follow_redirects=True,
                timeout=30,
            )
        except httpx.RequestError as exc:
            raise ExternalError("GitHub API unreachable") from exc
        if not response.is_success:
            raise ExternalError("Failed to fetch file from GitHub")
        return response.content

    def read_manifest(self, template_id: str) -> dict:
        import base64

        url = f"{GITHUB_API}/repos/{self.repo}/contents/{self.full_path(template_id)}/manifest.yaml"
        try:
            file_data = self.cached_get(url)
            content = base64.b64decode(file_data["content"]).decode("utf-8")  # type: ignore[index]
            return yaml.safe_load(content) or {}
        except NotFoundError:
            return {}

    def list_templates(self) -> list[GitHubTemplateSummary]:
        entries = self.list_repo_dir("")
        templates = []
        for entry in entries:
            if entry.get("type") != "dir":
                continue
            template_id = entry["name"]
            manifest = self.read_manifest(template_id)
            templates.append(
                GitHubTemplateSummary(
                    id=template_id,
                    name=manifest.get("name", template_id),
                    slug=manifest.get("slug"),
                    description=manifest.get("description", ""),
                    adapter_type=manifest.get("adapter_type", "claude_code"),
                    adapter_config=manifest.get("adapter_config", {}),
                    skills=manifest.get("skills", []),
                    tools=manifest.get("tools", ["Read", "Write", "Bash"]),
                    heartbeat_interval_seconds=manifest.get("heartbeat_interval_seconds", 0),
                    mode=manifest.get("mode", "no_pr"),
                )
            )
        return templates

    def get_template(self, template_id: str) -> GitHubTemplateSummary:
        url = f"{GITHUB_API}/repos/{self.repo}/contents/{self.full_path(template_id)}"
        entry = self.cached_get(url)
        if isinstance(entry, dict) and entry.get("type") != "dir":
            raise NotFoundError(f"Template '{template_id}' not found")

        manifest = self.read_manifest(template_id)

        return GitHubTemplateSummary(
            id=template_id,
            name=manifest.get("name", template_id),
            slug=manifest.get("slug"),
            description=manifest.get("description", ""),
            adapter_type=manifest.get("adapter_type", "claude_code"),
            adapter_config=manifest.get("adapter_config", {}),
            skills=manifest.get("skills", []),
            tools=manifest.get("tools", ["Read", "Write", "Bash"]),
            heartbeat_interval_seconds=manifest.get("heartbeat_interval_seconds", 0),
            mode=manifest.get("mode", "no_pr"),
        )

    def fetch_template_files(self, template_id: str) -> dict[str, bytes]:
        """Return all non-manifest files from {template_id}/ as in-memory bytes."""
        prefix = f"{template_id}/"
        full_prefix = self.full_prefix(prefix)
        blobs = self.list_tree_blobs(prefix)
        files: dict[str, bytes] = {}

        for blob in blobs:
            relative = blob["path"][len(full_prefix):]
            if relative in ("manifest.yaml", "manifest.json"):
                continue
            files[relative] = self.fetch_blob_bytes(blob["url"])

        return files

    def scaffold_agent_from_template(
        self,
        template_id: str,
        agent_slug: str,
        base_path: str,
    ) -> str:
        prefix = f"{template_id}/"
        full_prefix = self.full_prefix(prefix)
        blobs = self.list_tree_blobs(prefix)

        agent_dir = Path(base_path) / "agents" / agent_slug
        if agent_dir.exists():
            raise ConflictError(f"Agent directory already exists: {agent_dir}")
        agent_dir.mkdir(parents=True)

        for blob in blobs:
            blob_path = blob["path"]
            relative = blob_path[len(full_prefix):]
            if relative == "manifest.yaml":
                continue
            dest = agent_dir / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = self.fetch_blob_bytes(blob["url"])
            dest.write_bytes(content)

        (agent_dir / "memory").mkdir(exist_ok=True)
        (agent_dir / "runs").mkdir(exist_ok=True)

        return str(agent_dir)

    def read_skill_frontmatter(self, skill_id: str) -> dict:
        import base64

        url = f"{GITHUB_API}/repos/{self.repo}/contents/{self.full_path(skill_id)}/SKILL.md"
        try:
            file_data = self.cached_get(url)
            content = base64.b64decode(file_data["content"]).decode("utf-8")  # type: ignore[index]
        except NotFoundError:
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        return yaml.safe_load(parts[1]) or {}

    def list_skills(self) -> list[SkillSummary]:
        entries = self.list_repo_dir("")
        skills = []
        for entry in entries:
            if entry.get("type") != "dir":
                continue
            skill_id = entry["name"]
            front = self.read_skill_frontmatter(skill_id)
            skills.append(
                SkillSummary(
                    id=skill_id,
                    name=front.get("name", skill_id),
                    description=front.get("description", ""),
                )
            )
        return skills

    def fetch_skill_files(self, skill_id: str) -> dict[str, bytes]:
        """Return all files from {skill_id}/ recursively as in-memory bytes."""
        prefix = f"{skill_id}/"
        full_prefix = self.full_prefix(prefix)
        blobs = self.list_tree_blobs(prefix)
        files: dict[str, bytes] = {}
        for blob in blobs:
            relative = blob["path"][len(full_prefix):]
            files[relative] = self.fetch_blob_bytes(blob["url"])
        return files
