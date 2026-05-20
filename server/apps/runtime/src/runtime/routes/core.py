import os
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["core"])

VERSION = "0.1.0"

ADAPTER_DISPLAY_NAMES = {
    "claude_code": "Claude Code",
    "open_code": "OpenCode",
}


class RuntimeInfo(BaseModel):
    version: str
    status: str
    uptime_seconds: float
    pid: int


class AdapterItem(BaseModel):
    type: str
    name: str
    healthy: bool
    default_model: str


@router.get("/")
def root():
    return {"ok": True, "message": "zenve runtime is running", "version": VERSION}


@router.get("/healthz")
def healthz():
    return {"ok": True, "service": "zenve-runtime", "version": VERSION}


@router.get("/api/v1/runtime/info", response_model=RuntimeInfo)
def get_runtime_info(request: Request) -> RuntimeInfo:
    started_at: datetime = request.app.state.started_at
    uptime = (datetime.now(UTC) - started_at).total_seconds()
    return RuntimeInfo(
        version=VERSION,
        status="running",
        uptime_seconds=round(uptime, 1),
        pid=os.getpid(),
    )


@router.get("/api/v1/runtime/adapters", response_model=list[AdapterItem])
async def list_adapters(request: Request) -> list[AdapterItem]:
    registry = request.app.state.adapter_registry
    health: dict[str, bool] = await registry.health_check_all()
    items = []
    for adapter_type, healthy in health.items():
        adapter = registry.get(adapter_type)
        default_config = adapter.get_default_config()
        default_model = getattr(default_config, "model", "")
        items.append(AdapterItem(
            type=adapter_type,
            name=ADAPTER_DISPLAY_NAMES.get(adapter_type, adapter_type),
            healthy=healthy,
            default_model=default_model or "",
        ))
    return sorted(items, key=lambda a: a.name)
