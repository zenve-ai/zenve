from fastapi import Request

from runtime.services.run_service import RunService
from runtime.services.workspace_service import WorkspaceService


def get_workspace_service(request: Request) -> WorkspaceService:
    return request.app.state.workspace_service


def get_run_service(request: Request) -> RunService:
    return request.app.state.run_service
