from fastapi import Depends, Request
from sqlalchemy.orm import Session

from zenve_config.settings import Settings, get_settings
from zenve_db.database import get_db
from zenve_services.agent import AgentService
from zenve_services.api_key import ApiKeyService
from zenve_services.auth import AuthService
from zenve_services.github import GitHubService
from zenve_services.membership import MembershipService
from zenve_services.project import ProjectService
from zenve_services.repo_reader import RepoReaderService
from zenve_services.repo_writer import RepoWriterService
from zenve_services.template import GitHubTemplateService
from zenve_services.ws_manager import WebSocketManager


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


def get_membership_service(db: Session = Depends(get_db)) -> MembershipService:
    return MembershipService(db)


def get_api_key_service(db: Session = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(db)


def get_template_service(
    settings: Settings = Depends(get_settings),
) -> GitHubTemplateService:
    return GitHubTemplateService(settings)


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
