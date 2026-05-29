import json
import queue

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from runtime.models.errors import NotFoundError
from runtime.models.run import (
    RunHistory,
    RunTriggerRequest,
    RunTriggerResponse,
    WorkspaceRun,
)
from runtime.run_store import RunStore
from runtime.services import get_run_db_service, get_run_service, get_run_store, get_trigger_service
from runtime.services.run_db_service import RunDbService
from runtime.services.run_service import RunService
from runtime.services.run_trigger_service import RunTriggerService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/runs", tags=["runs"])


@router.post("", response_model=RunTriggerResponse, status_code=202)
def trigger_run(
    workspace_id: str,
    body: RunTriggerRequest,
    service: RunTriggerService = Depends(get_trigger_service),
):
    return service.trigger(workspace_id, body)


@router.get("", response_model=list[WorkspaceRun])
def list_runs(
    workspace_id: str,
    limit: int = 50,
    service: RunService = Depends(get_run_service),
):
    return service.list_grouped(workspace_id, limit=limit)


@router.get("/history", response_model=list[RunHistory])
def list_run_history(
    workspace_id: str,
    limit: int = 50,
    service: RunDbService = Depends(get_run_db_service),
):
    return service.list_runs(workspace_id, limit=limit)


@router.get("/active-run")
def get_active_run(
    workspace_id: str,
    run_store: RunStore = Depends(get_run_store),
):
    record = run_store.get_active_for_workspace(workspace_id)
    if record is None:
        return None
    return {"run_id": record.run_id, "status": record.status}


@router.get("/latest", response_model=WorkspaceRun | None)
def get_latest_run(
    workspace_id: str,
    service: RunService = Depends(get_run_service),
):
    return service.get_latest(workspace_id)


@router.get("/{run_id}", response_model=WorkspaceRun)
def get_run(
    workspace_id: str,
    run_id: str,
    service: RunService = Depends(get_run_service),
):
    return service.get_grouped(workspace_id, run_id)


@router.get("/{run_id}/events", response_model=list[dict])
def get_run_events(
    workspace_id: str,
    run_id: str,
    service: RunService = Depends(get_run_service),
):
    return service.get_events(workspace_id, run_id)


@router.get("/{run_id}/stream")
def stream_run_events(
    workspace_id: str,
    run_id: str,
    run_store: RunStore = Depends(get_run_store),
):
    if run_store.get(run_id) is None:
        raise NotFoundError(f"Run {run_id} not found")

    def generate():
        q = run_store.subscribe(run_id)
        try:
            while True:
                try:
                    event = q.get(timeout=30)
                    if event is None:
                        break
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            run_store.unsubscribe(run_id, q)

    return StreamingResponse(generate(), media_type="text/event-stream")
