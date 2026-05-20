from __future__ import annotations

from pydantic import BaseModel, Field


class IssueResponse(BaseModel):
    id: int
    title: str
    body: str = ""
    state: str = "open"
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class IssueCreateRequest(BaseModel):
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)


class IssueUpdateRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    state: str | None = None
    labels: list[str] | None = None
    assignees: list[str] | None = None


class CommentResponse(BaseModel):
    id: int
    issue_id: int
    body: str
    author: str = ""
    created_at: str = ""
    updated_at: str = ""


class CommentCreateRequest(BaseModel):
    body: str


class CommentUpdateRequest(BaseModel):
    body: str | None = None
