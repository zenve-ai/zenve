from __future__ import annotations

import httpx

GITHUB_API = "https://api.github.com"
DEFAULT_TIMEOUT = 30.0


class GitHubError(RuntimeError):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"GitHub API {status_code}: {body}")


class GitHubClient:
    """Thin wrapper over GitHub REST v3 — only the endpoints we use."""

    def __init__(self, token: str, repo: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.repo = repo
        self._client = httpx.Client(
            base_url=GITHUB_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        resp = self._client.request(method, path, **kwargs)
        if resp.is_error:
            raise GitHubError(resp.status_code, resp.text)
        return resp

    def list_open_issues(self) -> list[dict]:
        """Return open issues (excluding PRs) across all pages."""
        items: list[dict] = []
        page = 1
        while True:
            resp = self.request(
                "GET",
                f"/repos/{self.repo}/issues",
                params={"state": "open", "per_page": 100, "page": page},
            )
            batch = resp.json()
            if not batch:
                break
            items.extend(raw for raw in batch if "pull_request" not in raw)
            if len(batch) < 100:
                break
            page += 1
        return items

    def list_open_pulls(self) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            resp = self.request(
                "GET",
                f"/repos/{self.repo}/pulls",
                params={"state": "open", "per_page": 100, "page": page},
            )
            batch = resp.json()
            if not batch:
                break
            items.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return items

    def list_branches(self) -> list[str]:
        names: list[str] = []
        page = 1
        while True:
            resp = self.request(
                "GET",
                f"/repos/{self.repo}/branches",
                params={"per_page": 100, "page": page},
            )
            batch = resp.json()
            if not batch:
                break
            names.extend(item.get("name", "") for item in batch)
            if len(batch) < 100:
                break
            page += 1
        return names

    def add_labels(self, number: int, labels: list[str]) -> None:
        self.request(
            "POST",
            f"/repos/{self.repo}/issues/{number}/labels",
            json={"labels": labels},
        )

    def remove_label(self, number: int, label: str) -> None:
        self._client.delete(f"/repos/{self.repo}/issues/{number}/labels/{label}")

    def add_assignees(self, number: int, assignees: list[str]) -> None:
        self.request(
            "POST",
            f"/repos/{self.repo}/issues/{number}/assignees",
            json={"assignees": assignees},
        )

    def get_comments(self, number: int) -> list[dict]:
        """Return all comments for an issue or PR across all pages."""
        items: list[dict] = []
        page = 1
        while True:
            resp = self.request(
                "GET",
                f"/repos/{self.repo}/issues/{number}/comments",
                params={"per_page": 100, "page": page},
            )
            batch = resp.json()
            if not batch:
                break
            items.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return items

    def post_comment(self, number: int, body: str) -> None:
        self.request(
            "POST",
            f"/repos/{self.repo}/issues/{number}/comments",
            json={"body": body},
        )

    def viewer_login(self) -> str:
        resp = self.request("GET", "/user")
        return resp.json().get("login", "")

    def create_pr(self, title: str, body: str, head: str, base: str) -> str:
        """Open a pull request. Returns the PR HTML URL."""
        resp = self.request(
            "POST",
            f"/repos/{self.repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base},
        )
        return resp.json().get("html_url", "")
