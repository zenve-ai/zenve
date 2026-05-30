from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import zenve_core
from runtime.models.run import RunTriggerRequest, RunTriggerResponse
from runtime.run_store import RunStore
from runtime.services.run_db_service import RunDbService
from runtime.services.workspace_service import WorkspaceService
from runtime.ws_manager import WsManager
from zenve_core import AgentNotFoundError
from zenve_github import resolve_github_token

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_message(req: RunTriggerRequest) -> str:
    if req.message:
        return req.message
    return f"Work on issue #{req.issue_id}."


class RunTriggerService:
    def __init__(
        self,
        workspace_service: WorkspaceService,
        run_store: RunStore,
        ws_manager: WsManager,
        run_db_service: RunDbService,
    ) -> None:
        self.workspace_service = workspace_service
        self.run_store = run_store
        self.ws_manager = ws_manager
        self.run_db_service = run_db_service
        self._executor = ThreadPoolExecutor(max_workers=4)

    def trigger(self, workspace_id: str, req: RunTriggerRequest) -> RunTriggerResponse:
        detail = self.workspace_service.detail(workspace_id)
        project_dir = Path(detail.path)
        message = build_message(req)
        run_id = uuid4().hex
        self.run_store.create(run_id, workspace_id)
        self.run_db_service.create_run(run_id, workspace_id, req.agent, message, req.issue_id)
        self.ws_manager.broadcast(workspace_id, {
            "type": "run.created",
            "data": {"run_id": run_id, "workspace_id": workspace_id, "status": "queued"},
        })
        self._executor.submit(self.execute_run, run_id, workspace_id, project_dir, req, message)
        return RunTriggerResponse(run_id=run_id, status="queued")

    def execute_run(
        self,
        run_id: str,
        workspace_id: str,
        project_dir: Path,
        req: RunTriggerRequest,
        message: str,
    ) -> None:
        self.run_store.update_status(run_id, "running")
        self.run_db_service.set_run_running(run_id)
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

            github_token = resolve_github_token() or ""
            result = asyncio.run(
                zenve_core.run_agent(
                    project_dir=project_dir,
                    agent_slug=req.agent,
                    message=message,
                    workspace_id=workspace_id,
                    env_vars={"GH_TOKEN": github_token, **(req.env_vars or {})},
                    on_event=on_event,
                )
            )
            self.run_store.update_status(run_id, "done")
            self.run_db_service.set_run_finished(
                run_id=run_id,
                status=result.status,
                duration_seconds=result.duration_seconds,
                exit_code=result.exit_code,
                error=result.error,
                token_input=result.token_usage.input_tokens if result.token_usage else None,
                token_output=result.token_usage.output_tokens if result.token_usage else None,
                token_cost_usd=result.token_usage.cost_usd if result.token_usage else None,
            )
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": result.status, "finished_at": utcnow_iso()},
            })
        except AgentNotFoundError as exc:
            logger.error("agent not found run_id=%s: %s", run_id, exc)
            self.run_store.update_status(run_id, "failed")
            self.run_db_service.set_run_finished(run_id, "failed", error=str(exc))
            self.run_store.broadcast(run_id, {"type": "run.failed", "data": {"error": str(exc)}})
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": "failed", "finished_at": utcnow_iso()},
            })
        except Exception as exc:
            logger.error("run error run_id=%s: %s", run_id, exc)
            self.run_store.update_status(run_id, "failed")
            self.run_db_service.set_run_finished(run_id, "failed", error=str(exc))
            self.run_store.broadcast(run_id, {"type": "run.failed", "data": {"error": str(exc)}})
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": "failed", "finished_at": utcnow_iso()},
            })
        finally:
            self.run_store.close(run_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
