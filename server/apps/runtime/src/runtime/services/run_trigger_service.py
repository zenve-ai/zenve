from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import zenve_engine
from runtime.models.run import RunTriggerRequest, RunTriggerResponse
from runtime.run_store import RunStore
from runtime.services.run_db_service import RunDbService
from runtime.services.workspace_service import WorkspaceService
from runtime.ws_manager import WsManager
from zenve_engine import DirtyTreeError, EngineError, MissingRemoteBranchError
from zenve_engine.config import load_project_settings
from zenve_engine.env import resolve_github_token

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


AGENT_TERMINAL_EVENTS = {
    "agent.completed",
    "agent.failed",
    "agent.needs_input",
    "agent.changes_requested",
    "agent.nothing_to_do",
    "agent.misconfigured",
}


class RunTriggerService:
    def __init__(
        self,
        workspace_service: WorkspaceService,
        run_store: RunStore,
        ws_manager: WsManager,
        run_db_service: RunDbService,
        issues_adapter_type: str = "github",
    ) -> None:
        self.workspace_service = workspace_service
        self.run_store = run_store
        self.ws_manager = ws_manager
        self.run_db_service = run_db_service
        self.issues_adapter_type = issues_adapter_type
        self._executor = ThreadPoolExecutor(max_workers=4)

    def trigger(self, workspace_id: str, req: RunTriggerRequest) -> RunTriggerResponse:
        detail = self.workspace_service.detail(workspace_id)
        github_token = resolve_github_token() or ""
        project_dir = Path(detail.path)
        project = load_project_settings(project_dir)
        adapter_type = project.issues.adapter or self.issues_adapter_type
        run_id = uuid4().hex
        self.run_store.create(run_id, workspace_id)
        self.run_db_service.create_run(run_id, workspace_id)
        self.ws_manager.broadcast(workspace_id, {
            "type": "run.created",
            "data": {"run_id": run_id, "workspace_id": workspace_id, "status": "queued"},
        })
        self._executor.submit(
            self.execute_run, run_id, project_dir, detail.repo or detail.project, github_token, adapter_type, req
        )
        return RunTriggerResponse(run_id=run_id, status="queued")

    def execute_run(
        self,
        run_id: str,
        project_dir: Path,
        repo: str,
        github_token: str,
        issues_adapter_type: str,
        req: RunTriggerRequest,
    ) -> None:
        workspace_id = self.run_store.get(run_id).workspace_id
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
                self.handle_agent_event(run_id, event)

            report = zenve_engine.run(
                project_dir=project_dir,
                run_id=run_id,
                github_token=github_token,
                repo=repo,
                only_agent=req.only_agent,
                env_vars=req.env_vars,
                on_event=on_event,
                issues_adapter_type=issues_adapter_type,
                auto_commit_zenve=True,
            )
            for rf in report.results:
                try:
                    self.run_db_service.update_agent_result(
                        run_id=run_id,
                        agent_name=rf.agent,
                        item_type=rf.item.type if rf.item else None,
                        item_number=rf.item.number if rf.item else None,
                        item_title=rf.item.title if rf.item else None,
                        duration_seconds=rf.duration_seconds,
                        pipeline_from=rf.pipeline_transition.from_label if rf.pipeline_transition else None,
                        pipeline_to=rf.pipeline_transition.to_label if rf.pipeline_transition else None,
                        token_input=rf.token_usage.input_tokens if rf.token_usage else None,
                        token_output=rf.token_usage.output_tokens if rf.token_usage else None,
                        token_cost_usd=rf.token_usage.cost_usd if rf.token_usage else None,
                    )
                except Exception:
                    logger.warning("Failed to persist result for agent %s run %s", rf.agent, run_id)
            self.run_store.update_status(run_id, "done")
            self.run_db_service.set_run_finished(run_id, "completed", outcome=report.summary or None)
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": "done", "outcome": None, "finished_at": utcnow_iso()},
            })
        except (DirtyTreeError, MissingRemoteBranchError, EngineError) as exc:
            logger.error("run failed run_id=%s: %s", run_id, exc)
            self.run_store.update_status(run_id, "failed")
            self.run_db_service.set_run_finished(run_id, "failed", error=str(exc))
            self.run_store.broadcast(run_id, {"type": "run.failed", "data": {"error": str(exc)}})
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": "failed", "outcome": None, "finished_at": utcnow_iso()},
            })
        except Exception as exc:
            logger.error("run error run_id=%s: %s", run_id, exc)
            self.run_store.update_status(run_id, "failed")
            self.run_db_service.set_run_finished(run_id, "failed", error=str(exc))
            self.run_store.broadcast(run_id, {"type": "run.failed", "data": {"error": str(exc)}})
            self.ws_manager.broadcast(workspace_id, {
                "type": "run.finished",
                "data": {"run_id": run_id, "status": "failed", "outcome": None, "finished_at": utcnow_iso()},
            })
        finally:
            self.run_store.close(run_id)

    def handle_agent_event(self, run_id: str, event: dict) -> None:
        event_type = event.get("type", "")
        agent_name = event.get("agent")
        if not agent_name or (event_type not in AGENT_TERMINAL_EVENTS and event_type != "agent.started"):
            return
        data = event.get("data") or {}
        try:
            if event_type == "agent.started":
                self.run_db_service.upsert_agent(run_id, agent_name, "running")
            elif event_type == "agent.nothing_to_do":
                self.run_db_service.upsert_agent(run_id, agent_name, "skipped", skip_reason="no task picked up", set_finished=True)
            elif event_type == "agent.misconfigured":
                self.run_db_service.upsert_agent(run_id, agent_name, "misconfigured", skip_reason=data.get("reason"), set_finished=True)
            elif event_type == "agent.completed":
                self.run_db_service.upsert_agent(run_id, agent_name, "completed", exit_code=data.get("exit_code"), set_finished=True)
            elif event_type == "agent.failed":
                self.run_db_service.upsert_agent(run_id, agent_name, "failed", exit_code=data.get("exit_code"), error=data.get("error"), set_finished=True)
            elif event_type == "agent.needs_input":
                self.run_db_service.upsert_agent(run_id, agent_name, "needs_input", set_finished=True)
            elif event_type == "agent.changes_requested":
                self.run_db_service.upsert_agent(run_id, agent_name, "changes_requested", set_finished=True)
        except Exception:
            logger.warning("Failed to write agent event to DB run_id=%s agent=%s type=%s", run_id, agent_name, event_type)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
