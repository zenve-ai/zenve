from fastapi import APIRouter, Depends, Header, HTTPException, status

from zenve.config.settings import settings
from zenve.db.models import ApiKeyRecord, Organization
from zenve.models.api_key import ApiKeyCreate, ApiKeyCreated
from zenve.models.org import OrgCreate, OrgResponse, OrgUpdate
from zenve.services import get_api_key_service, get_org_service
from zenve.services.api_key import ApiKeyService
from zenve.services.org import OrgService
from zenve.utils.api_key_auth import get_current_org

router = APIRouter(prefix="/api/v1/orgs", tags=["organizations"])


class OrgCreatedResponse(OrgResponse):
    api_key: ApiKeyCreated


@router.post("", response_model=OrgCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_org(
    body: OrgCreate,
    org_service: OrgService = Depends(get_org_service),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
    authorization: str | None = Header(None, alias="Authorization"),
):
    # Protect bootstrap with setup token if configured
    if settings.setup_token:
        if not authorization or authorization != f"Bearer {settings.setup_token}":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Setup token required to create organizations",
            )

    org = org_service.create(body)
    key_data = ApiKeyCreate(name="Default API Key")
    record, raw_key = api_key_service.create(org.id, key_data)

    api_key_resp = ApiKeyCreated.model_validate(record, from_attributes=True).model_copy(
        update={"raw_key": raw_key}
    )
    return OrgCreatedResponse(
        **OrgResponse.model_validate(org, from_attributes=True).model_dump(),
        api_key=api_key_resp,
    )


@router.get("", response_model=list[OrgResponse])
def list_orgs(
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    service: OrgService = Depends(get_org_service),
):
    org, _ = auth
    return [org]


@router.get("/{org_id}", response_model=OrgResponse)
def get_org(
    org_id: str,
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    service: OrgService = Depends(get_org_service),
):
    org, _ = auth
    target = service.get_by_id_or_slug(org_id)
    if target.id != org.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return target


@router.patch("/{org_id}", response_model=OrgResponse)
def update_org(
    org_id: str,
    body: OrgUpdate,
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    service: OrgService = Depends(get_org_service),
):
    org, _ = auth
    if org_id != org.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return service.update(org_id, body)
