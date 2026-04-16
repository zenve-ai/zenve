from __future__ import annotations

from pydantic import BaseModel


class WorkerRegisterRequest(BaseModel):
    org_slug: str
    queue: str
    runtimes: list[str]


class WorkerRegisterResponse(BaseModel):
    ok: bool


class RunContextFile(BaseModel):
    path: str
    content: str


class RunContextResponse(BaseModel):
    files: list[RunContextFile]
    run_context: dict
    adapter_type: str
    adapter_config: dict
    message: str | None
    heartbeat: bool
    env_vars: dict


class RunCompleteRequest(BaseModel):
    exit_code: int
    stdout: str
    stderr: str | None = None
    token_usage: dict | None = None
    duration_seconds: float


class RunCompleteResponse(BaseModel):
    ok: bool
