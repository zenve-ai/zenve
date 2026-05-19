from __future__ import annotations

import os
import subprocess
from typing import ClassVar

import httpx

from zenve_issues.base import BaseIssueAdapter
from zenve_issues.models import (
    Comment,
    CommentCreate,
    CommentNotFoundError,
    CommentUpdate,
    GitHubIssueConfig,
    Issue,
    IssueAdapterError,
    IssueCreate,
    IssueListFilter,
    IssueNotFoundError,
    IssueUpdate,
)

GITHUB_API = "https://api.github.com"


class GitHubIssueError(RuntimeError):
    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"GitHub API error {status_code}: {body}")
        self.status_code = status_code
        self.body = body


def resolve_token(config: GitHubIssueConfig) -> str:
    """Resolve a GitHub token using the same priority as zenve_engine.env.

    1. config.token (if provided)
    2. ZENVE_GH_TOKEN env var
    3. `gh auth token` subprocess
    4. Raises IssueAdapterError if none found
    """
    if config.token:
        return config.token
    if token := os.environ.get("ZENVE_GH_TOKEN"):
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        if token:
            return token
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    raise IssueAdapterError("No GitHub token. Run `gh auth login`.")


class GitHubIssueAdapter(BaseIssueAdapter):
    adapter_type: ClassVar[str] = "github"

    def __init__(self, config: GitHubIssueConfig) -> None:
        super().__init__(config)

    @classmethod
    def validate_config(cls, raw_config: dict) -> GitHubIssueConfig:
        return GitHubIssueConfig.model_validate(raw_config)

    def create(self, data: IssueCreate) -> Issue:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        payload: dict = {"title": data.title, "body": data.body}
        if data.labels:
            payload["labels"] = data.labels
        if data.assignees:
            payload["assignees"] = data.assignees
        with self._client(cfg, token) as client:
            raw = self._request(client, "POST", f"/repos/{cfg.repo}/issues", json=payload)
        return self._raw_to_issue(raw)

    def list(self, filters: IssueListFilter | None = None) -> list[Issue]:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        f = filters or IssueListFilter()
        params: dict = {"state": f.state, "per_page": 100, "page": 1}
        if f.assignee:
            params["assignee"] = f.assignee
        if f.labels:
            params["labels"] = ",".join(f.labels)

        issues: list[Issue] = []
        with self._client(cfg, token) as client:
            while True:
                raw_list = self._request(client, "GET", f"/repos/{cfg.repo}/issues", params=params)
                for raw in raw_list:
                    if "pull_request" in raw:
                        continue
                    issues.append(self._raw_to_issue(raw))
                    if f.limit is not None and len(issues) >= f.limit:
                        return issues
                if len(raw_list) < 100:
                    break
                params["page"] += 1
        return issues

    def get(self, issue_id: int) -> Issue:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        with self._client(cfg, token) as client:
            try:
                raw = self._request(client, "GET", f"/repos/{cfg.repo}/issues/{issue_id}")
            except GitHubIssueError as e:
                if e.status_code == 404:
                    raise IssueNotFoundError(issue_id) from e
                raise IssueAdapterError(str(e)) from e
        return self._raw_to_issue(raw)

    def update(self, issue_id: int, data: IssueUpdate) -> Issue:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        payload = data.model_dump(exclude_none=True)
        with self._client(cfg, token) as client:
            raw = self._request(client, "PATCH", f"/repos/{cfg.repo}/issues/{issue_id}", json=payload)
        return self._raw_to_issue(raw)

    def delete(self, issue_id: int) -> None:
        self.update(issue_id, IssueUpdate(state="closed"))

    def health_check(self) -> bool:
        try:
            cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
            token = resolve_token(cfg)
            with self._client(cfg, token) as client:
                self._request(client, "GET", "/user")
            return True
        except Exception:
            return False

    def _client(self, cfg: GitHubIssueConfig, token: str) -> httpx.Client:
        return httpx.Client(
            base_url=GITHUB_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=cfg.timeout,
        )

    def _request(self, client: httpx.Client, method: str, path: str, **kwargs) -> dict | list | None:
        response = client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise GitHubIssueError(response.status_code, response.text)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _raw_to_comment(self, raw: dict) -> Comment:
        issue_id = int(raw["issue_url"].rsplit("/", 1)[-1])
        return Comment(
            id=raw["id"],
            issue_id=issue_id,
            body=raw.get("body") or "",
            author=raw["user"]["login"],
            created_at=raw.get("created_at", ""),
            updated_at=raw.get("updated_at", ""),
        )

    def add_comment(self, issue_id: int, data: CommentCreate) -> Comment:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        with self._client(cfg, token) as client:
            raw = self._request(
                client, "POST",
                f"/repos/{cfg.repo}/issues/{issue_id}/comments",
                json={"body": data.body},
            )
        return self._raw_to_comment(raw)

    def list_comments(self, issue_id: int) -> list[Comment]:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        params: dict = {"per_page": 100, "page": 1}
        comments: list[Comment] = []
        with self._client(cfg, token) as client:
            while True:
                raw_list = self._request(
                    client, "GET",
                    f"/repos/{cfg.repo}/issues/{issue_id}/comments",
                    params=params,
                )
                for raw in raw_list:
                    comments.append(self._raw_to_comment(raw))
                if len(raw_list) < 100:
                    break
                params["page"] += 1
        return comments

    def get_comment(self, comment_id: int) -> Comment:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        with self._client(cfg, token) as client:
            try:
                raw = self._request(
                    client, "GET",
                    f"/repos/{cfg.repo}/issues/comments/{comment_id}",
                )
            except GitHubIssueError as e:
                if e.status_code == 404:
                    raise CommentNotFoundError(comment_id) from e
                raise IssueAdapterError(str(e)) from e
        return self._raw_to_comment(raw)

    def update_comment(self, comment_id: int, data: CommentUpdate) -> Comment:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        payload = data.model_dump(exclude_none=True)
        with self._client(cfg, token) as client:
            try:
                raw = self._request(
                    client, "PATCH",
                    f"/repos/{cfg.repo}/issues/comments/{comment_id}",
                    json=payload,
                )
            except GitHubIssueError as e:
                if e.status_code == 404:
                    raise CommentNotFoundError(comment_id) from e
                raise IssueAdapterError(str(e)) from e
        return self._raw_to_comment(raw)

    def delete_comment(self, comment_id: int) -> None:
        cfg: GitHubIssueConfig = self.config  # type: ignore[assignment]
        token = resolve_token(cfg)
        with self._client(cfg, token) as client:
            try:
                self._request(
                    client, "DELETE",
                    f"/repos/{cfg.repo}/issues/comments/{comment_id}",
                )
            except GitHubIssueError as e:
                if e.status_code == 404:
                    raise CommentNotFoundError(comment_id) from e
                raise IssueAdapterError(str(e)) from e

    def _raw_to_issue(self, raw: dict) -> Issue:
        return Issue(
            id=raw["number"],
            title=raw["title"],
            body=raw.get("body") or "",
            state=raw.get("state", "open"),
            labels=[lbl["name"] for lbl in raw.get("labels", [])],
            assignees=[a["login"] for a in raw.get("assignees", [])],
            created_at=raw.get("created_at", ""),
            updated_at=raw.get("updated_at", ""),
        )
