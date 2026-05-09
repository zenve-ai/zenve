from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    model_config = {"extra": "ignore"}

    number: int
    kind: Literal["issue", "pull_request"]
    agent_name: str
    run_id: str
    claimed_at: str  # ISO-8601 UTC, e.g. "2026-04-29T10:00:00Z"


class ClaimsFile(BaseModel):
    model_config = {"extra": "ignore"}

    claims: list[Claim] = Field(default_factory=list)
