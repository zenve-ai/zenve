import base64
import os
import time

import httpx
import yaml

from runtime.models.errors import ExternalError, NotFoundError, RateLimitError, ValidationError
from runtime.models.template import SkillFilesResponse, SkillItem, TemplateFilesResponse, TemplateItem

GITHUB_API = "https://api.github.com"
CACHE_TTL = 300.0


class TemplateService:
    def __init__(self) -> None:
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.agents_repo = os.environ.get("GITHUB_AGENTS_REPO")
        self.agents_base = "agents"
        self.skills_base = "skills"
        self.cache: dict[str, tuple[object, float]] = {}

    def require_repo(self) -> str:
        if not self.agents_repo:
            raise ValidationError("GITHUB_AGENTS_REPO is not configured")
        return self.agents_repo

    def auth_headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def cached_get(self, url: str, params: dict | None = None) -> object:
        cache_key = url + str(sorted((params or {}).items()))
        now = time.monotonic()
        if cache_key in self.cache:
            data, expires_at = self.cache[cache_key]
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
        self.cache[cache_key] = (data, now + CACHE_TTL)
        return data

    def list_repo_dir(self, repo: str, path: str) -> list[dict]:
        url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
        result = self.cached_get(url)
        if not isinstance(result, list):
            raise NotFoundError(f"Path '{path}' is not a directory")
        return result

    def get_head_sha(self, repo: str) -> str | None:
        for branch in ("main", "master"):
            try:
                ref_data = self.cached_get(f"{GITHUB_API}/repos/{repo}/git/ref/heads/{branch}")
            except NotFoundError:
                continue
            try:
                return ref_data["object"]["sha"]  # type: ignore[index]
            except (KeyError, TypeError):
                return None
        return None

    def list_tree_blobs(self, repo: str, tree_sha: str, prefix: str) -> list[dict]:
        tree_url = f"{GITHUB_API}/repos/{repo}/git/trees/{tree_sha}"
        tree_data = self.cached_get(tree_url, params={"recursive": "1"})
        tree = tree_data["tree"]  # type: ignore[index]
        return [
            item
            for item in tree
            if item.get("type") == "blob" and item.get("path", "").startswith(prefix)
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

    def read_manifest(self, repo: str, base: str, template_id: str) -> dict:
        url = f"{GITHUB_API}/repos/{repo}/contents/{base}/{template_id}/manifest.yaml"
        try:
            file_data = self.cached_get(url)
            content = base64.b64decode(file_data["content"]).decode("utf-8")  # type: ignore[index]
            return yaml.safe_load(content) or {}
        except NotFoundError:
            return {}

    def list_templates(self) -> list[TemplateItem]:
        repo = self.require_repo()
        entries = self.list_repo_dir(repo, self.agents_base)
        templates = []
        for entry in entries:
            if entry.get("type") != "dir":
                continue
            template_id = entry["name"]
            manifest = self.read_manifest(repo, self.agents_base, template_id)
            templates.append(
                TemplateItem(
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

    def get_template(self, template_id: str) -> TemplateItem:
        repo = self.require_repo()
        url = f"{GITHUB_API}/repos/{repo}/contents/{self.agents_base}/{template_id}"
        entry = self.cached_get(url)
        if isinstance(entry, dict) and entry.get("type") != "dir":
            raise NotFoundError(f"Template '{template_id}' not found")
        manifest = self.read_manifest(repo, self.agents_base, template_id)
        return TemplateItem(
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

    def get_template_files(self, template_id: str) -> TemplateFilesResponse:
        repo = self.require_repo()
        sha = self.get_head_sha(repo)
        if sha is None:
            raise NotFoundError(f"No default branch found in repo {repo}")
        prefix = f"{self.agents_base}/{template_id}/"
        blobs = self.list_tree_blobs(repo, sha, prefix)
        files: dict[str, str] = {}
        for blob in blobs:
            relative = blob["path"][len(prefix):]
            if relative in ("manifest.yaml", "manifest.json"):
                continue
            content = self.fetch_blob_bytes(blob["url"])
            files[relative] = base64.b64encode(content).decode()
        return TemplateFilesResponse(sha=sha, source=repo, files=files)

    def read_skill_frontmatter(self, repo: str, skill_id: str) -> dict:
        url = f"{GITHUB_API}/repos/{repo}/contents/{self.skills_base}/{skill_id}/SKILL.md"
        try:
            file_data = self.cached_get(url)
            content = base64.b64decode(file_data["content"]).decode("utf-8")  # type: ignore[index]
        except NotFoundError:
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        return yaml.safe_load(parts[1]) or {}

    def list_skills(self) -> list[SkillItem]:
        repo = self.require_repo()
        entries = self.list_repo_dir(repo, self.skills_base)
        skills = []
        for entry in entries:
            if entry.get("type") != "dir":
                continue
            skill_id = entry["name"]
            front = self.read_skill_frontmatter(repo, skill_id)
            skills.append(
                SkillItem(
                    id=skill_id,
                    name=front.get("name", skill_id),
                    description=front.get("description", ""),
                )
            )
        return skills

    def get_skill_files(self, skill_id: str) -> SkillFilesResponse:
        repo = self.require_repo()
        sha = self.get_head_sha(repo)
        if sha is None:
            raise NotFoundError(f"No default branch found in repo {repo}")
        prefix = f"{self.skills_base}/{skill_id}/"
        blobs = self.list_tree_blobs(repo, sha, prefix)
        files: dict[str, str] = {}
        for blob in blobs:
            relative = blob["path"][len(prefix):]
            content = self.fetch_blob_bytes(blob["url"])
            files[relative] = base64.b64encode(content).decode()
        return SkillFilesResponse(files=files)
