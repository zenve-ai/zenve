from fastapi import APIRouter, Depends

from runtime.models.template import TemplateFilesResponse, TemplateItem
from runtime.services import get_template_service
from runtime.services.template_service import TemplateService

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


@router.get("", response_model=list[TemplateItem])
def list_templates(svc: TemplateService = Depends(get_template_service)) -> list[TemplateItem]:
    return svc.list_templates()


@router.get("/{template_id}", response_model=TemplateItem)
def get_template(
    template_id: str,
    svc: TemplateService = Depends(get_template_service),
) -> TemplateItem:
    return svc.get_template(template_id)


@router.get("/{template_id}/files", response_model=TemplateFilesResponse)
def get_template_files(
    template_id: str,
    svc: TemplateService = Depends(get_template_service),
) -> TemplateFilesResponse:
    return svc.get_template_files(template_id)
