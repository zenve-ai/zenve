from __future__ import annotations

from pathlib import Path

from runtime.models.errors import ExternalError, NotFoundError
from runtime.models.issue import (
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    IssueCreateRequest,
    IssueResponse,
    IssueUpdateRequest,
)
from runtime.services.workspace_service import WorkspaceService
from zenve_engine.api import build_issues_adapter
from zenve_engine.config import load_project_settings
from zenve_engine.env import resolve_github_token
from zenve_issues import BaseIssueAdapter
from zenve_issues.models import (
    CommentCreate,
    CommentNotFoundError,
    CommentUpdate,
    IssueCreate,
    IssueListFilter,
    IssueNotFoundError,
    IssueUpdate,
)


def issue_to_response(issue) -> IssueResponse:
    return IssueResponse(
        id=issue.id,
        title=issue.title,
        body=issue.body,
        state=issue.state,
        labels=issue.labels,
        assignees=issue.assignees,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        url=issue.url,
    )


def comment_to_response(comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        issue_id=comment.issue_id,
        body=comment.body,
        author=comment.author,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


class IssueService:
    def __init__(self, workspace_service: WorkspaceService, issues_adapter_type: str = "github") -> None:
        self.workspace_service = workspace_service
        self.issues_adapter_type = issues_adapter_type

    def get_adapter(self, workspace_id: str) -> BaseIssueAdapter:
        detail = self.workspace_service.detail(workspace_id)
        github_token = resolve_github_token() or ""
        if not github_token:
            raise ExternalError("No GitHub token. Set ZENVE_GH_TOKEN or run `gh auth login`.")
        project_dir = Path(detail.path)
        project = load_project_settings(project_dir)
        adapter_type = project.issues.adapter or self.issues_adapter_type
        repo = detail.repo or ""
        return build_issues_adapter(adapter_type, project_dir, github_token, repo)

    def list_issues(self, workspace_id: str, state: str = "open", limit: int | None = None) -> list[IssueResponse]:
        adapter = self.get_adapter(workspace_id)
        issues = adapter.list(IssueListFilter(state=state, limit=limit))
        return [issue_to_response(i) for i in issues]

    def get_issue(self, workspace_id: str, issue_id: int) -> IssueResponse:
        adapter = self.get_adapter(workspace_id)
        try:
            return issue_to_response(adapter.get(issue_id))
        except IssueNotFoundError:
            raise NotFoundError(f"Issue #{issue_id} not found")

    def create_issue(self, workspace_id: str, data: IssueCreateRequest) -> IssueResponse:
        adapter = self.get_adapter(workspace_id)
        issue = adapter.create(IssueCreate(
            title=data.title,
            body=data.body,
            labels=data.labels,
            assignees=data.assignees,
        ))
        return issue_to_response(issue)

    def update_issue(self, workspace_id: str, issue_id: int, data: IssueUpdateRequest) -> IssueResponse:
        adapter = self.get_adapter(workspace_id)
        try:
            issue = adapter.update(issue_id, IssueUpdate(
                title=data.title,
                body=data.body,
                state=data.state,
                labels=data.labels,
                assignees=data.assignees,
            ))
        except IssueNotFoundError:
            raise NotFoundError(f"Issue #{issue_id} not found")
        return issue_to_response(issue)

    def delete_issue(self, workspace_id: str, issue_id: int) -> None:
        adapter = self.get_adapter(workspace_id)
        try:
            adapter.delete(issue_id)
        except IssueNotFoundError:
            raise NotFoundError(f"Issue #{issue_id} not found")

    def list_comments(self, workspace_id: str, issue_id: int) -> list[CommentResponse]:
        adapter = self.get_adapter(workspace_id)
        try:
            comments = adapter.list_comments(issue_id)
        except IssueNotFoundError:
            raise NotFoundError(f"Issue #{issue_id} not found")
        return [comment_to_response(c) for c in comments]

    def add_comment(self, workspace_id: str, issue_id: int, data: CommentCreateRequest) -> CommentResponse:
        adapter = self.get_adapter(workspace_id)
        try:
            comment = adapter.add_comment(issue_id, CommentCreate(body=data.body))
        except IssueNotFoundError:
            raise NotFoundError(f"Issue #{issue_id} not found")
        return comment_to_response(comment)

    def update_comment(self, workspace_id: str, issue_id: int, comment_id: int, data: CommentUpdateRequest) -> CommentResponse:
        adapter = self.get_adapter(workspace_id)
        try:
            comment = adapter.update_comment(comment_id, CommentUpdate(body=data.body))
        except CommentNotFoundError:
            raise NotFoundError(f"Comment #{comment_id} not found")
        return comment_to_response(comment)

    def delete_comment(self, workspace_id: str, issue_id: int, comment_id: int) -> None:
        adapter = self.get_adapter(workspace_id)
        try:
            adapter.delete_comment(comment_id)
        except CommentNotFoundError:
            raise NotFoundError(f"Comment #{comment_id} not found")

    def list_labels(self, workspace_id: str) -> list[str]:
        adapter = self.get_adapter(workspace_id)
        return adapter.list_labels()
