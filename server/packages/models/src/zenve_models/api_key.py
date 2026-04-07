from datetime import datetime

from pydantic import BaseModel, field_validator


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["*"]
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: str
    org_id: str
    name: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}

    @field_validator("scopes", mode="before")
    @classmethod
    def parse_scopes(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v  # type: ignore[return-value]


class ApiKeyCreated(ApiKeyResponse):
    raw_key: str
