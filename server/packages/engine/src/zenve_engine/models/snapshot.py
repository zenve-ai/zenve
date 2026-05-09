from __future__ import annotations

from pydantic import BaseModel, Field


class SnapshotComment(BaseModel):
    model_config = {"extra": "ignore"}

    author: str
    body: str
    created_at: str


class SnapshotIssue(BaseModel):
    model_config = {"extra": "ignore"}

    number: int
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    state: str = "open"
    created_at: str = ""
    comments: list[SnapshotComment] = Field(default_factory=list)


class SnapshotPR(BaseModel):
    model_config = {"extra": "ignore"}

    number: int
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    state: str = "open"
    head: str = ""
    base: str = ""
    draft: bool = False
    created_at: str = ""
    comments: list[SnapshotComment] = Field(default_factory=list)


class Snapshot(BaseModel):
    """Shape of `.zenve/snapshot.json`."""

    model_config = {"extra": "ignore"}

    fetched_at: str
    run_id: str
    issues: list[SnapshotIssue] = Field(default_factory=list)
    pull_requests: list[SnapshotPR] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
