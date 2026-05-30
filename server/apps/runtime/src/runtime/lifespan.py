import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from runtime.db.database import Base, get_engine, migrate_runs_columns
from runtime.db.models import (  # noqa: F401 — registers ORM models with Base
    RunRecord,
    UserRecord,
)
from runtime.models.config import RuntimeConfig
from runtime.run_store import RunStore
from runtime.services.issue_service import IssueService
from runtime.services.pr_service import PRService
from runtime.services.run_db_service import RunDbService
from runtime.services.run_service import RunService
from runtime.services.run_trigger_service import RunTriggerService
from runtime.services.settings_service import SettingsService
from runtime.services.template_service import TemplateService
from runtime.services.workspace_service import WorkspaceService
from runtime.ws_manager import WsManager
from zenve_adapters import build_default_registry

PID_FILE = Path.home() / ".zenve" / "runtime.pid"
LOG_FILE = Path.home() / ".zenve" / "runtime.log"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging here — uvicorn calls dictConfig() before lifespan runs,
    # so any basicConfig() at module level gets overwritten. Configuring here wins.
    LOG_FILE.parent.mkdir(exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(logging.StreamHandler())

    root.addHandler(logging.FileHandler(LOG_FILE))
    for handler in root.handlers:
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))

    logger.info("=" * 60)
    logger.info("Starting Zenve Runtime")
    logger.info("=" * 60)

    Base.metadata.create_all(bind=get_engine())
    migrate_runs_columns()
    logger.info("Database initialized: %s", "~/.zenve/zenve.db")

    config = RuntimeConfig.load()
    logger.info("Issues adapter: %s", config.issues_adapter)

    loop = asyncio.get_event_loop()
    ws_manager = WsManager(loop)
    run_store = RunStore()

    # Services
    settings_service = SettingsService()
    workspace_service = WorkspaceService()
    run_db_service = RunDbService()
    run_service = RunService(workspace_service, run_db_service)
    trigger_service = RunTriggerService(workspace_service, run_store, ws_manager, run_db_service)
    issue_service = IssueService(workspace_service, config.issues_adapter)
    pr_service = PRService(workspace_service)
    template_service = TemplateService()

    app.state.ws_manager = ws_manager
    app.state.run_store = run_store

    # Register services
    app.state.run_db_service = run_db_service
    app.state.settings_service = settings_service
    app.state.workspace_service = workspace_service
    app.state.run_service = run_service
    app.state.trigger_service = trigger_service
    app.state.issue_service = issue_service
    app.state.pr_service = pr_service
    app.state.template_service = template_service
    app.state.adapter_registry = build_default_registry()
    app.state.started_at = datetime.now(UTC)

    logger.info(f"Registry loaded: {len(workspace_service.list())} workspace(s) registered")
    PID_FILE.parent.mkdir(exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    yield

    trigger_service.shutdown()
    PID_FILE.unlink(missing_ok=True)
    logger.info("zenve runtime shutdown complete")
