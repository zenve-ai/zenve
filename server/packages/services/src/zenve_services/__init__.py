from fastapi import Depends, Request
from sqlalchemy.orm import Session

from zenve_adapters.registry import AdapterRegistry
from zenve_config.settings import Settings, get_settings
from zenve_db.database import get_db
from zenve_services.agent import AgentService
from zenve_services.api_key import ApiKeyService
from zenve_services.auth import AuthService
from zenve_services.github import GitHubService
from zenve_services.membership import MembershipService
from zenve_services.project import ProjectService
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


def get_adapter_registry(request: Request) -> AdapterRegistry:
    return request.app.state.adapter_registry


def get_template_service(
    settings: Settings = Depends(get_settings),
) -> GitHubTemplateService:
    return GitHubTemplateService(settings)


def get_agent_service(
    db: Session = Depends(get_db),
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    template_service: GitHubTemplateService = Depends(get_template_service),
) -> AgentService:
    return AgentService(db, adapter_registry, template_service)


def get_github_service(db: Session = Depends(get_db)) -> GitHubService:
    return GitHubService(db)


def get_repo_writer_service() -> RepoWriterService:
    return RepoWriterService()


def get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager
