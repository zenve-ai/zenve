from fastapi import Depends, Request
from sqlalchemy.orm import Session

from zenve_adapters.registry import AdapterRegistry
from zenve_config.settings import Settings, get_settings
from zenve_db.database import get_db
from zenve_scaffolding import PresetService, ScaffoldingService
from zenve_services.agent import AgentService
from zenve_services.api_key import ApiKeyService
from zenve_services.auth import AuthService
from zenve_services.filesystem import FilesystemService
from zenve_services.membership import MembershipService
from zenve_services.org import OrgService
from zenve_services.run import RunService
from zenve_services.template import TemplateService


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_org_service(db: Session = Depends(get_db)) -> OrgService:
    return OrgService(db)


def get_membership_service(db: Session = Depends(get_db)) -> MembershipService:
    return MembershipService(db)


def get_api_key_service(db: Session = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(db)


def get_filesystem_service(
    settings: Settings = Depends(get_settings),
) -> FilesystemService:
    return FilesystemService(settings)


def get_adapter_registry(request: Request) -> AdapterRegistry:
    return request.app.state.adapter_registry


def get_template_service(
    settings: Settings = Depends(get_settings),
) -> TemplateService:
    return TemplateService(settings)


def get_scaffolding_service(
    settings: Settings = Depends(get_settings),
) -> ScaffoldingService:
    return ScaffoldingService(settings)


def get_preset_service() -> PresetService:
    return PresetService()


def get_agent_service(
    db: Session = Depends(get_db),
    filesystem: FilesystemService = Depends(get_filesystem_service),
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    template_service: TemplateService = Depends(get_template_service),
    scaffolding: ScaffoldingService = Depends(get_scaffolding_service),
    preset_service: PresetService = Depends(get_preset_service),
) -> AgentService:
    return AgentService(
        db, filesystem, adapter_registry, template_service, scaffolding, preset_service
    )


def get_run_service(db: Session = Depends(get_db)) -> RunService:
    return RunService(db)
