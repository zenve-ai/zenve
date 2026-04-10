from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RunCreate(BaseModel):
    agent: str
    message: str | None = None


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    agent_id: str
    trigger: str
    status: str
    adapter_type: str
    message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    exit_code: int | None
    error_summary: str | None
    token_usage: dict | None
    transcript_path: str | None
    created_at: datetime


class RunTranscript(BaseModel):
    run_id: str
    content: str
