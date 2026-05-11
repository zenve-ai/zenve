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
    to_label: list[str] | None = None


class TokenUsage(BaseModel):
    model_config = {"extra": "ignore"}

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None


class WorkspaceRunSummary(BaseModel):
    """Summary of a single agent run on disk under `.zenve/agents/{slug}/runs/{run_id}.json`."""

    model_config = {"extra": "ignore"}

    run_id: str
    agent: str
    started_at: str
    finished_at: str
    duration_seconds: float
    status: str
    exit_code: int


class WorkspaceRunDetail(WorkspaceRunSummary):
    """Full run record — mirrors `RunResultFile` shape written by the CLI."""

    item: RunItem | None = None
    output: str | None = None
    pipeline_transition: PipelineTransition | None = None
    token_usage: TokenUsage | None = None
    error: str | None = None


class WorkspaceRun(BaseModel):
    """All agent results for a single run, grouped by run_id."""

    run_id: str
    started_at: str
    finished_at: str
    status: str
    agents: list[WorkspaceRunSummary]


class RunTriggerRequest(BaseModel):
    only_agent: str | None = None
    env_vars: dict[str, str] | None = None


class RunTriggerResponse(BaseModel):
    run_id: str
    status: Literal["queued"]
