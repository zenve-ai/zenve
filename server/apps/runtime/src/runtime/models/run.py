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
    """Summary of a single agent run sourced from the DB."""

    model_config = {"extra": "ignore"}

    run_id: str
    agent: str
    started_at: str
    finished_at: str
    duration_seconds: float
    status: str
    exit_code: int


class WorkspaceRunDetail(WorkspaceRunSummary):
    """Full run record sourced from the DB."""

    item: RunItem | None = None
    pipeline_transition: PipelineTransition | None = None
    token_usage: TokenUsage | None = None
    error: str | None = None


class WorkspaceRun(BaseModel):
    """All agent results for a single run, grouped by run_id."""

    run_id: str
    started_at: str
    finished_at: str
    status: str
    error: str | None = None
    agents: list[WorkspaceRunSummary]


class AgentStats(BaseModel):
    agent: str
    total_runs: int
    completed_runs: int
    failed_runs: int
    runs: list[RunHistoryAgent]


class RunTriggerRequest(BaseModel):
    only_agent: str | None = None
    env_vars: dict[str, str] | None = None


class RunTriggerResponse(BaseModel):
    run_id: str
    status: Literal["queued"]


class RunHistoryAgent(BaseModel):
    run_id: str
    agent_name: str
    status: str
    skip_reason: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    error: str | None = None
    item_type: str | None = None
    item_number: int | None = None
    item_title: str | None = None
    duration_seconds: float | None = None
    pipeline_from: str | None = None
    pipeline_to: list[str] | None = None
    token_input: int | None = None
    token_output: int | None = None
    token_cost_usd: float | None = None


class RunHistory(BaseModel):
    run_id: str
    workspace_id: str
    status: str
    error: str | None = None
    triggered_at: str
    started_at: str | None = None
    finished_at: str | None = None
    outcome: str | None = None
    agents: list[RunHistoryAgent] = []
