from __future__ import annotations

from pydantic import BaseModel, Field


class PRCommentResponse(BaseModel):
    author: str = ""
    body: str = ""
    created_at: str = ""


class PRResponse(BaseModel):
    number: int
    title: str
    body: str = ""
    state: str = "open"
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    head: str = ""
    base: str = ""
    draft: bool = False
    created_at: str = ""
    url: str | None = None
    comments: list[PRCommentResponse] = Field(default_factory=list)
