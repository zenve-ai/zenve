from fastapi import APIRouter, Depends, HTTPException

from zenve_models.github_template import GitHubTemplateSummary
from zenve_services import get_template_service
from zenve_services.template import GitHubTemplateService

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


def require_enabled(service: GitHubTemplateService = Depends(get_template_service)) -> GitHubTemplateService:
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="GitHub agent templates are not configured")
    return service


@router.get("", response_model=list[GitHubTemplateSummary])
def list_templates(
    service: GitHubTemplateService = Depends(require_enabled),
):
    return service.list_templates()


@router.get("/{template_id}", response_model=GitHubTemplateSummary)
def get_template(
    template_id: str,
    service: GitHubTemplateService = Depends(require_enabled),
):
    return service.get_template(template_id)
