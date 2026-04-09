from fastapi import APIRouter, Depends

from zenve_models.template import TemplateManifest, TemplateSummary
from zenve_services import get_template_service
from zenve_services.template import TemplateService

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


@router.get("", response_model=list[TemplateSummary])
def list_templates(
    service: TemplateService = Depends(get_template_service),
):
    return service.list_templates()


@router.get("/{template_name}", response_model=TemplateManifest)
def get_template(
    template_name: str,
    service: TemplateService = Depends(get_template_service),
):
    return service.get_manifest(template_name)
