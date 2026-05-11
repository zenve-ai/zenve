from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import zenve_engine
from runtime.models.run import RunTriggerRequest, RunTriggerResponse
from runtime.run_store import RunStore
from runtime.services.workspace_service import WorkspaceService
from zenve_engine import DirtyTreeError, EngineError, MissingRemoteBranchError

logger = logging.getLogger(__name__)


class RunTriggerService:
    def __init__(self, workspace_service: WorkspaceService, run_store: RunStore) -> None:
        self.workspace_service = workspace_service
        self.run_store = run_store
        self._executor = ThreadPoolExecutor(max_workers=4)

    def trigger(self, workspace_id: str, req: RunTriggerRequest) -> RunTriggerResponse:
        detail = self.workspace_service.detail(workspace_id)
        github_token = os.environ.get("GITHUB_TOKEN", "")
        run_id = uuid4().hex
        self.run_store.create(run_id, workspace_id)
        self._executor.submit(
            self.execute_run, run_id, Path(detail.path), detail.project, github_token, req
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
        self.run_store.update_status(run_id, "running")
        try:
            zenve_engine.run(
                project_dir=project_dir,
                run_id=run_id,
                github_token=github_token,
                repo=repo,
                only_agent=req.only_agent,
                env_vars=req.env_vars,
                on_event=lambda event: logger.info("run_event run_id=%s event=%s", run_id, event),
            )
            self.run_store.update_status(run_id, "done")
        except (DirtyTreeError, MissingRemoteBranchError, EngineError) as exc:
            logger.error("run failed run_id=%s: %s", run_id, exc)
            self.run_store.update_status(run_id, "failed")

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
