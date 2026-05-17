from __future__ import annotations

from pydantic import BaseModel, Field


class IssueAdapterConfigBase(BaseModel):
    model_config = {"extra": "ignore"}


class GitHubIssueConfig(IssueAdapterConfigBase):
    token: str | None = None
    repo: str
    timeout: float = 30.0


class SQLiteIssueConfig(IssueAdapterConfigBase):
    db_path: str


class Issue(BaseModel):
    model_config = {"extra": "ignore"}

    id: int
    title: str
    body: str = ""
    state: str = "open"
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class IssueCreate(BaseModel):
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)


class IssueUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    state: str | None = None
    labels: list[str] | None = None
    assignees: list[str] | None = None


class IssueListFilter(BaseModel):
    state: str = "open"
    labels: list[str] = Field(default_factory=list)
    assignee: str | None = None
    limit: int | None = None


class IssueNotFoundError(RuntimeError):
    def __init__(self, issue_id: int) -> None:
        super().__init__(f"Issue not found: {issue_id}")


class IssueAdapterError(RuntimeError):
    pass
