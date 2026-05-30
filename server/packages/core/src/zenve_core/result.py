from __future__ import annotations

from pydantic import BaseModel

from zenve_core.models.run_result import TokenUsage


class AgentRunResult(BaseModel):
    run_id: str
    agent_slug: str
    agent_name: str
    started_at: str
    finished_at: str
    duration_seconds: float
    status: str  # completed | failed | needs_input | changes_requested
    exit_code: int
    output: str | None = None
    error: str | None = None
    token_usage: TokenUsage | None = None
