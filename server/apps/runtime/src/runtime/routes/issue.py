from fastapi import APIRouter, Depends

from runtime.models.issue import (
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    IssueCreateRequest,
    IssueResponse,
    IssueUpdateRequest,
)
from runtime.services import get_issue_service
from runtime.services.issue_service import IssueService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/issues", tags=["issues"])


@router.get("", response_model=list[IssueResponse])
def list_issues(
    workspace_id: str,
    state: str = "open",
    limit: int | None = None,
    service: IssueService = Depends(get_issue_service),
):
    return service.list_issues(workspace_id, state=state, limit=limit)


@router.post("", response_model=IssueResponse, status_code=201)
def create_issue(
    workspace_id: str,
    body: IssueCreateRequest,
    service: IssueService = Depends(get_issue_service),
):
    return service.create_issue(workspace_id, body)


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(
    workspace_id: str,
    issue_id: int,
    service: IssueService = Depends(get_issue_service),
):
    return service.get_issue(workspace_id, issue_id)


@router.patch("/{issue_id}", response_model=IssueResponse)
def update_issue(
    workspace_id: str,
    issue_id: int,
    body: IssueUpdateRequest,
    service: IssueService = Depends(get_issue_service),
):
    return service.update_issue(workspace_id, issue_id, body)


@router.delete("/{issue_id}", status_code=204)
def delete_issue(
    workspace_id: str,
    issue_id: int,
    service: IssueService = Depends(get_issue_service),
):
    service.delete_issue(workspace_id, issue_id)


# --- Comments ---

@router.get("/{issue_id}/comments", response_model=list[CommentResponse])
def list_comments(
    workspace_id: str,
    issue_id: int,
    service: IssueService = Depends(get_issue_service),
):
    return service.list_comments(workspace_id, issue_id)


@router.post("/{issue_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(
    workspace_id: str,
    issue_id: int,
    body: CommentCreateRequest,
    service: IssueService = Depends(get_issue_service),
):
    return service.add_comment(workspace_id, issue_id, body)


@router.patch("/{issue_id}/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    workspace_id: str,
    issue_id: int,
    comment_id: int,
    body: CommentUpdateRequest,
    service: IssueService = Depends(get_issue_service),
):
    return service.update_comment(workspace_id, issue_id, comment_id, body)


@router.delete("/{issue_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    workspace_id: str,
    issue_id: int,
    comment_id: int,
    service: IssueService = Depends(get_issue_service),
):
    service.delete_comment(workspace_id, issue_id, comment_id)
