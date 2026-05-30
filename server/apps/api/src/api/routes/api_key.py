from fastapi import APIRouter, Depends, HTTPException, status

from api.db.models import ApiKeyRecord, Workspace
from api.models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from api.services import get_api_key_service
from api.services.api_key import ApiKeyService
from api.services.api_key_auth import get_current_workspace

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    workspace_id: str,
    body: ApiKeyCreate,
    auth: tuple[Workspace, ApiKeyRecord] = Depends(get_current_workspace),
    service: ApiKeyService = Depends(get_api_key_service),
):
    workspace, _ = auth
    record, raw_key = service.create(workspace.id, body)
    base = ApiKeyResponse.model_validate(record, from_attributes=True)
    return ApiKeyCreated(**base.model_dump(), raw_key=raw_key)


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    workspace_id: str,
    auth: tuple[Workspace, ApiKeyRecord] = Depends(get_current_workspace),
    service: ApiKeyService = Depends(get_api_key_service),
):
    workspace, _ = auth
    return service.list_by_org(workspace.id)


@router.delete("/{key_id}", response_model=ApiKeyResponse)
def revoke_api_key(
    workspace_id: str,
    key_id: str,
    auth: tuple[Workspace, ApiKeyRecord] = Depends(get_current_workspace),
    service: ApiKeyService = Depends(get_api_key_service),
):
    workspace, _ = auth
    record = service.revoke(key_id)
    if record.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="API key not found")
    return record
