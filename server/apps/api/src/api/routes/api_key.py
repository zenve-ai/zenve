from fastapi import APIRouter, Depends, HTTPException, status

from zenve_db.models import ApiKeyRecord, Project
from zenve_models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from zenve_services import get_api_key_service
from zenve_services.api_key import ApiKeyService
from zenve_services.api_key_auth import get_current_project

router = APIRouter(prefix="/api/v1/projects/{project_id}/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    project_id: str,
    body: ApiKeyCreate,
    auth: tuple[Project, ApiKeyRecord] = Depends(get_current_project),
    service: ApiKeyService = Depends(get_api_key_service),
):
    project, _ = auth
    record, raw_key = service.create(project.id, body)
    base = ApiKeyResponse.model_validate(record, from_attributes=True)
    return ApiKeyCreated(**base.model_dump(), raw_key=raw_key)


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    project_id: str,
    auth: tuple[Project, ApiKeyRecord] = Depends(get_current_project),
    service: ApiKeyService = Depends(get_api_key_service),
):
    project, _ = auth
    return service.list_by_org(project.id)


@router.delete("/{key_id}", response_model=ApiKeyResponse)
def revoke_api_key(
    project_id: str,
    key_id: str,
    auth: tuple[Project, ApiKeyRecord] = Depends(get_current_project),
    service: ApiKeyService = Depends(get_api_key_service),
):
    project, _ = auth
    record = service.revoke(key_id)
    if record.project_id != project.id:
        raise HTTPException(status_code=404, detail="API key not found")
    return record
