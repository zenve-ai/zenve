from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class RunItem(BaseModel):
    model_config = {"extra": "ignore"}

    type: Literal["issue", "pull_request"]
    number: int
    title: str


class PipelineTransition(BaseModel):
    model_config = {"extra": "ignore"}

    from_label: str
    to_label: str | None


class TokenUsage(BaseModel):
    model_config = {"extra": "ignore"}

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None


class RunResultFile(BaseModel):
    """Shape of `.zenve/agents/{name}/runs/{run_id}.json`."""

    model_config = {"extra": "ignore"}

    run_id: str
    agent: str
    started_at: str
    finished_at: str
    duration_seconds: float
    status: str
    exit_code: int
    item: RunItem | None = None
    output: dict = {}
    pipeline_transition: PipelineTransition | None = None
    token_usage: TokenUsage | None = None
    error: str | None = None
