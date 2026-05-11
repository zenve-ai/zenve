import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

PID_FILE = Path.home() / ".zenve" / "runtime.pid"

from runtime.run_store import RunStore
from runtime.services.run_service import RunService
from runtime.services.run_trigger_service import RunTriggerService
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
    app.state.run_store = run_store
    app.state.workspace_service = workspace_service
    app.state.run_service = run_service
    app.state.trigger_service = trigger_service

    logger.info(f"Registry loaded: {len(workspace_service.list())} workspace(s) registered")
    PID_FILE.parent.mkdir(exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    yield

    trigger_service.shutdown()
    PID_FILE.unlink(missing_ok=True)
    logger.info("zenve runtime shutdown complete")
