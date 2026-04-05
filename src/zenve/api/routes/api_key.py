from fastapi import APIRouter, Depends, status

from zenve.db.models import ApiKeyRecord, Organization
from zenve.models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from zenve.services import get_api_key_service
from zenve.services.api_key import ApiKeyService
from zenve.utils.api_key_auth import get_current_org

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: ApiKeyCreate,
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    service: ApiKeyService = Depends(get_api_key_service),
):
    org, _ = auth
    record, raw_key = service.create(org.id, body)
    return ApiKeyCreated.model_validate(record, from_attributes=True).model_copy(
        update={"raw_key": raw_key}
    )


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    service: ApiKeyService = Depends(get_api_key_service),
):
    org, _ = auth
    return service.list_by_org(org.id)


@router.delete("/{key_id}", response_model=ApiKeyResponse)
def revoke_api_key(
    key_id: str,
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    service: ApiKeyService = Depends(get_api_key_service),
):
    org, _ = auth
    record = service.revoke(key_id)
    if record.org_id != org.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="API key not found")
    return record
