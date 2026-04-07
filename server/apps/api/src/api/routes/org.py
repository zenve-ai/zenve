from fastapi import APIRouter, Depends, status

from zenve_db.models import UserRecord
from zenve_models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from zenve_models.org import (
    OrgCreate,
    OrgCreatedResponse,
    OrgResponse,
    OrgUpdate,
    OrgWithRoleResponse,
)
from zenve_services import get_api_key_service, get_membership_service, get_org_service
from zenve_services.api_key import ApiKeyService
from zenve_services.membership import MembershipService
from zenve_services.org import OrgService
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/orgs", tags=["organizations"])


@router.post("", response_model=OrgCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_org(
    body: OrgCreate,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    org = org_service.create(body, owner_user_id=user.id)
    key_data = ApiKeyCreate(name="Default API Key")
    record, raw_key = api_key_service.create(org.id, key_data)

    base = ApiKeyResponse.model_validate(record, from_attributes=True)
    api_key_resp = ApiKeyCreated(**base.model_dump(), raw_key=raw_key)
    return OrgCreatedResponse(
        **OrgResponse.model_validate(org, from_attributes=True).model_dump(),
        api_key=api_key_resp,
    )


@router.get("", response_model=list[OrgWithRoleResponse])
def list_orgs(
    user: UserRecord = Depends(get_current_user),
    service: OrgService = Depends(get_org_service),
):
    results = service.list_for_user(user.id)
    return [
        OrgWithRoleResponse(
            **OrgResponse.model_validate(org, from_attributes=True).model_dump(),
            role=role,
        )
        for org, role in results
    ]


@router.get("/{org_id}", response_model=OrgWithRoleResponse)
def get_org(
    org_id: str,
    user: UserRecord = Depends(get_current_user),
    service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    org = service.get_by_id_or_slug(org_id)
    membership = membership_service.require_membership(user.id, org.id)
    return OrgWithRoleResponse(
        **OrgResponse.model_validate(org, from_attributes=True).model_dump(),
        role=membership.role,
    )


@router.patch("/{org_id}", response_model=OrgWithRoleResponse)
def update_org(
    org_id: str,
    body: OrgUpdate,
    user: UserRecord = Depends(get_current_user),
    service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    org = service.get_by_id_or_slug(org_id)
    membership = membership_service.require_role(user.id, org.id, ["owner"])
    updated = service.update(org.id, body)
    return OrgWithRoleResponse(
        **OrgResponse.model_validate(updated, from_attributes=True).model_dump(),
        role=membership.role,
    )
