from fastapi import Depends
from sqlalchemy.orm import Session

from zenve.config.settings import Settings, get_settings
from zenve.db.database import get_db
from zenve.services.agent import AgentService
from zenve.services.api_key import ApiKeyService
from zenve.services.auth import AuthService
from zenve.services.filesystem import FilesystemService
from zenve.services.org import OrgService


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_org_service(db: Session = Depends(get_db)) -> OrgService:
    return OrgService(db)


def get_api_key_service(db: Session = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(db)


def get_filesystem_service(settings: Settings = Depends(get_settings)) -> FilesystemService:
    return FilesystemService(settings)


def get_agent_service(
    db: Session = Depends(get_db),
    filesystem: FilesystemService = Depends(get_filesystem_service),
) -> AgentService:
    return AgentService(db, filesystem)
