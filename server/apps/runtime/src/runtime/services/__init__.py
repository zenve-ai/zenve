from fastapi import Request

from runtime.run_store import RunStore
from runtime.services.issue_service import IssueService
from runtime.services.run_service import RunService
from runtime.services.run_trigger_service import RunTriggerService
from runtime.services.snapshot_service import SnapshotService
from runtime.services.template_service import TemplateService
from runtime.services.workspace_service import WorkspaceService
from runtime.ws_manager import WsManager


def get_workspace_service(request: Request) -> WorkspaceService:
    return request.app.state.workspace_service


def get_run_service(request: Request) -> RunService:
    return request.app.state.run_service


def get_trigger_service(request: Request) -> RunTriggerService:
    return request.app.state.trigger_service


def get_run_store(request: Request) -> RunStore:
    return request.app.state.run_store


def get_snapshot_service(request: Request) -> SnapshotService:
    return request.app.state.snapshot_service


def get_template_service(request: Request) -> TemplateService:
    return request.app.state.template_service


def get_ws_manager(request: Request) -> WsManager:
    return request.app.state.ws_manager


def get_issue_service(request: Request) -> IssueService:
    return request.app.state.issue_service
