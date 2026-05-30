from fastapi import Depends, Request
from sqlalchemy.orm import Session

from api.config import Settings, get_settings
from api.db.database import get_db
from api.services.agent import AgentService
from api.services.api_key import ApiKeyService
from api.services.auth import AuthService
from api.services.github import GitHubService
from api.services.membership import MembershipService
from api.services.workspace import WorkspaceService
from api.services.repo_reader import RepoReaderService
from api.services.repo_writer import RepoWriterService
from api.services.template import GitHubTemplateService
from api.services.ws_manager import WebSocketManager


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_workspace_service(db: Session = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(db)


def get_membership_service(db: Session = Depends(get_db)) -> MembershipService:
    return MembershipService(db)


def get_api_key_service(db: Session = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(db)


def get_template_service(
    settings: Settings = Depends(get_settings),
) -> GitHubTemplateService:
    return GitHubTemplateService(settings, base_path="agents")


def get_repo_writer_service() -> RepoWriterService:
    return RepoWriterService()


def get_repo_reader_service() -> RepoReaderService:
    return RepoReaderService()


def get_agent_service(
    reader: RepoReaderService = Depends(get_repo_reader_service),
    writer: RepoWriterService = Depends(get_repo_writer_service),
    template_service: GitHubTemplateService = Depends(get_template_service),
) -> AgentService:
    return AgentService(reader, writer, template_service)


def get_github_service(db: Session = Depends(get_db)) -> GitHubService:
    return GitHubService(db)


def get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager
