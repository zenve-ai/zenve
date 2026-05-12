import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

PID_FILE = Path.home() / ".zenve" / "runtime.pid"

from runtime.run_store import RunStore
from runtime.services.run_service import RunService
from runtime.services.run_trigger_service import RunTriggerService
from runtime.services.scheduler_service import SchedulerService
from runtime.services.snapshot_service import SnapshotService
from runtime.services.template_service import TemplateService
from runtime.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Starting Zenve Runtime")
    logger.info("=" * 60)

    run_store = RunStore()
    workspace_service = WorkspaceService()
    run_service = RunService(workspace_service)
    trigger_service = RunTriggerService(workspace_service, run_store)
    scheduler_service = SchedulerService(workspace_service, trigger_service)
    snapshot_service = SnapshotService(workspace_service)
    template_service = TemplateService()
    app.state.run_store = run_store
    app.state.workspace_service = workspace_service
    app.state.run_service = run_service
    app.state.trigger_service = trigger_service
    app.state.scheduler_service = scheduler_service
    app.state.snapshot_service = snapshot_service
    app.state.template_service = template_service

    logger.info(f"Registry loaded: {len(workspace_service.list())} workspace(s) registered")
    PID_FILE.parent.mkdir(exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    scheduler_service.start()

    yield

    trigger_service.shutdown()
    scheduler_service.shutdown()
    PID_FILE.unlink(missing_ok=True)
    logger.info("zenve runtime shutdown complete")
