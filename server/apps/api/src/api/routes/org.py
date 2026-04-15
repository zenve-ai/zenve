import secrets
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Depends, HTTPException, status

from zenve_config.settings import Settings, get_settings
from zenve_db.models import ApiKeyRecord, Organization, UserRecord
from zenve_models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from zenve_models.org import (
    OrgCreate,
    OrgCreatedResponse,
    OrgMeResponse,
    OrgResponse,
    OrgUpdate,
    OrgWithRoleResponse,
)
from zenve_services import (
    get_api_key_service,
    get_membership_service,
    get_org_service,
    get_redis_acl_service,
)
from zenve_services.api_key import ApiKeyService
from zenve_services.api_key_auth import get_current_org
from zenve_services.membership import MembershipService
from zenve_services.org import OrgService
from zenve_services.redis_acl import RedisACLService
from zenve_utils.api_key import hash_api_key
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/orgs", tags=["organizations"])


def build_redis_worker_url(base_url: str, username: str, password: str) -> str:
    """Embed org worker credentials into the gateway's Redis URL."""
    p = urlparse(base_url)
    netloc = f"{username}:{password}@{p.hostname}"
    if p.port:
        netloc += f":{p.port}"
    return urlunparse(p._replace(netloc=netloc))


@router.get("/me", response_model=OrgMeResponse)
def get_org_me(
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
):
    """Return the org identified by the API key.

    Includes redis_username for the org's worker queue.
    The Redis password is never returned here — it was shown once at org creation.
    """
    org, _ = auth
    return OrgMeResponse.model_validate(org, from_attributes=True)


@router.post("", response_model=OrgCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: OrgCreate,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
    settings: Settings = Depends(get_settings),
    redis_acl: RedisACLService | None = Depends(get_redis_acl_service),
):
    # Flush org + membership — not committed yet so Redis failure can abort cleanly.
    org = org_service.create_draft(body, owner_user_id=user.id)

    redis_worker_url = None
    redis_username = None
    redis_password_hash = None

    if redis_acl:
        plain_password = secrets.token_urlsafe(32)
        try:
            await redis_acl.create_org_user(org.slug, plain_password)
        except Exception as exc:
            org_service.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Org created but Redis worker user failed: {exc}",
            ) from exc

        redis_username = f"worker.{org.slug}"
        redis_password_hash = hash_api_key(plain_password)
        redis_worker_url = build_redis_worker_url(settings.redis_url, redis_username, plain_password)

    org = org_service.commit_create(
        org,
        redis_username=redis_username,
        redis_password_hash=redis_password_hash,
    )

    key_data = ApiKeyCreate(name="Default API Key")
    record, raw_key = api_key_service.create(org.id, key_data)

    base = ApiKeyResponse.model_validate(record, from_attributes=True)
    api_key_resp = ApiKeyCreated(**base.model_dump(), raw_key=raw_key)
    return OrgCreatedResponse(
        **OrgResponse.model_validate(org, from_attributes=True).model_dump(),
        api_key=api_key_resp,
        redis_worker_url=redis_worker_url,
    )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(
    org_id: str,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    redis_acl: RedisACLService | None = Depends(get_redis_acl_service),
):
    """Delete an org. Removes the Redis ACL user first (best-effort), then the DB record."""
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_role(user.id, org.id, ["owner"])

    if redis_acl and org.redis_username:
        # Failure is logged inside delete_org_user but does not block deletion.
        await redis_acl.delete_org_user(org.slug)

    org_service.delete(org.id)


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
