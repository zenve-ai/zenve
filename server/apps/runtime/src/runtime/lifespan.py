import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from runtime.services.run_service import RunService
from runtime.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Starting Zenve Runtime")
    logger.info("=" * 60)

    workspace_service = WorkspaceService()
    run_service = RunService(workspace_service)
    app.state.workspace_service = workspace_service
    app.state.run_service = run_service

    logger.info(f"Registry loaded: {len(workspace_service.list())} workspace(s) registered")

    yield

    logger.info("zenve runtime shutdown complete")
