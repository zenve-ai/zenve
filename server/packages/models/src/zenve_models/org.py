from datetime import datetime

from pydantic import BaseModel

from zenve_models.api_key import ApiKeyCreated


class OrgCreate(BaseModel):
    name: str
    slug: str | None = None


class OrgUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    base_path: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrgWithRoleResponse(OrgResponse):
    role: str


class OrgCreatedResponse(OrgResponse):
    api_key: ApiKeyCreated
    role: str = "owner"
