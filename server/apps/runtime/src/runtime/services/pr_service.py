from __future__ import annotations

from runtime.models.errors import ExternalError, NotFoundError, ValidationError
from runtime.models.pr import PRCommentResponse, PRResponse
from runtime.services.workspace_service import WorkspaceService
from zenve_engine.env import resolve_github_token
from zenve_engine.github.client import GitHubClient, GitHubError


def gh_pr_to_response(raw: dict, comments: list[dict] | None = None) -> PRResponse:
    return PRResponse(
        number=raw["number"],
        title=raw.get("title", ""),
        body=raw.get("body") or "",
        state=raw.get("state", "open"),
        labels=[label["name"] for label in raw.get("labels", [])],
        assignees=[a["login"] for a in raw.get("assignees", [])],
        head=raw.get("head", {}).get("ref", ""),
        base=raw.get("base", {}).get("ref", ""),
        draft=raw.get("draft", False),
        created_at=raw.get("created_at", ""),
        url=raw.get("html_url"),
        comments=[
            PRCommentResponse(
                author=c.get("user", {}).get("login", ""),
                body=c.get("body", ""),
                created_at=c.get("created_at", ""),
            )
            for c in (comments or [])
        ],
    )


class PRService:
    def __init__(self, workspace_service: WorkspaceService) -> None:
        self.workspace_service = workspace_service

    def get_client(self, workspace_id: str) -> GitHubClient:
        detail = self.workspace_service.detail(workspace_id)
        if not detail.repo:
            raise ValidationError(f"No GitHub remote detected for workspace at {detail.path}")
        token = resolve_github_token()
        if not token:
            raise ExternalError("No GitHub token. Set ZENVE_GH_TOKEN or run `gh auth login`.")
        return GitHubClient(token, detail.repo)

    def list_prs(self, workspace_id: str, state: str = "open", limit: int = 50) -> list[PRResponse]:
        # Open PRs are naturally few; apply the limit only for closed/all to avoid huge fetches.
        effective_limit = None if state == "open" else limit
        with self.get_client(workspace_id) as client:
            pulls = client.list_pulls(state, limit=effective_limit)
        return [gh_pr_to_response(raw) for raw in pulls]

    def get_pr(self, workspace_id: str, pr_number: int) -> PRResponse:
        with self.get_client(workspace_id) as client:
            try:
                raw = client.get_pull(pr_number)
            except GitHubError as exc:
                if exc.status_code == 404:
                    raise NotFoundError(f"Pull request #{pr_number} not found")
                raise
            comments = client.get_comments(pr_number)
        return gh_pr_to_response(raw, comments)
