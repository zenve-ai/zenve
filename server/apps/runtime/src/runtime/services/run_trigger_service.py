from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import zenve_engine
from runtime.models.run import RunTriggerRequest, RunTriggerResponse
from runtime.run_store import RunStore
from runtime.services.workspace_service import WorkspaceService
from runtime.ws_manager import WsManager
from zenve_engine import DirtyTreeError, EngineError, MissingRemoteBranchError
from zenve_engine.env import resolve_github_token

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunTriggerService:
    def __init__(self, workspace_service: WorkspaceService, run_store: RunStore, ws_manager: WsManager) -> None:
        self.workspace_service = workspace_service
        self.run_store = run_store
        self.ws_manager = ws_manager
        self._executor = ThreadPoolExecutor(max_workers=4)

    def trigger(self, workspace_id: str, req: RunTriggerRequest) -> RunTriggerResponse:
        detail = self.workspace_service.detail(workspace_id)
        github_token = resolve_github_token() or ""
        run_id = uuid4().hex
        self.run_store.create(run_id, workspace_id)
        self.ws_manager.broadcast(workspace_id, {
            "type": "run.created",
            "data": {"run_id": run_id, "workspace_id": workspace_id, "status": "queued"},
        })
        self._executor.submit(
            self.execute_run, run_id, Path(detail.path), detail.repo or detail.project, github_token, req
        )
        return RunTriggerResponse(run_id=run_id, status="queued")

    def execute_run(
        self,
        run_id: str,
        project_dir: Path,
        repo: str,
        github_token: str,
        req: RunTriggerRequest,
    ) -> None:
        workspace_id = self.run_store.get(run_id).workspace_id
        self.run_store.update_status(run_id, "running")
        self.ws_manager.broadcast(workspace_id, {
            "type": "run.status_changed",
            "data": {"run_id": run_id, "status": "running", "started_at": utcnow_iso()},
        })
        try:
            def on_event(event: dict) -> None:
                logger.info("run_event run_id=%s event=%s", run_id, event)
                self.run_store.broadcast(run_id, event)
                self.ws_manager.broadcast(workspace_id, {
                    "type": "run.event",
                    "data": {"run_id": run_id, **event},
                })

            zenve_engine.run(
                project_dir=project_dir,
                run_id=run_id,
                github_token=github_token,
                repo=repo,
                only_agent=req.only_agent,
                env_vars=req.env_vars,
                on_event=on_event,
            )
            self.run_store.update_status(run_id, "done")
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": "done", "outcome": None, "finished_at": utcnow_iso()},
            })
        except (DirtyTreeError, MissingRemoteBranchError, EngineError) as exc:
            logger.error("run failed run_id=%s: %s", run_id, exc)
            self.run_store.update_status(run_id, "failed")
            self.run_store.broadcast(run_id, {"type": "run.failed", "data": {"error": str(exc)}})
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": "failed", "outcome": None, "finished_at": utcnow_iso()},
            })
        finally:
            self.run_store.close(run_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
