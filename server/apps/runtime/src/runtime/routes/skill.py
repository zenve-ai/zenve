from fastapi import APIRouter, Depends

from runtime.models.template import SkillFilesResponse, SkillItem
from runtime.services import get_template_service
from runtime.services.template_service import TemplateService

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.get("", response_model=list[SkillItem])
def list_skills(svc: TemplateService = Depends(get_template_service)) -> list[SkillItem]:
    return svc.list_skills()


@router.get("/{skill_id}/files", response_model=SkillFilesResponse)
def get_skill_files(
    skill_id: str,
    svc: TemplateService = Depends(get_template_service),
) -> SkillFilesResponse:
    return svc.get_skill_files(skill_id)
