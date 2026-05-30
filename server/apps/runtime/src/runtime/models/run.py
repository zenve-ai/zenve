from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class TokenUsage(BaseModel):
    model_config = {"extra": "ignore"}

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None


class WorkspaceRunSummary(BaseModel):
    model_config = {"extra": "ignore"}

    run_id: str
    agent: str
    message: str | None = None
    issue_id: int | None = None
    status: str
    triggered_at: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    exit_code: int | None = None


class WorkspaceRunDetail(WorkspaceRunSummary):
    token_usage: TokenUsage | None = None
    error: str | None = None


class AgentStats(BaseModel):
    agent: str
    total_runs: int
    completed_runs: int
    failed_runs: int
    runs: list[WorkspaceRunDetail]


class RunTriggerRequest(BaseModel):
    agent: str
    message: str | None = None
    issue_id: int | None = None
    env_vars: dict[str, str] | None = None

    @model_validator(mode="after")
    def require_message_or_issue(self) -> RunTriggerRequest:
        if not self.message and not self.issue_id:
            raise ValueError("Provide either message or issue_id")
        return self


class RunTriggerResponse(BaseModel):
    run_id: str
    status: Literal["queued"]
