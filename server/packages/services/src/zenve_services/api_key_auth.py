from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from zenve_db.database import get_db
from zenve_db.models import ApiKeyRecord, Project
from zenve_services.api_key import ApiKeyService
from zenve_services.project import ProjectService


async def get_current_project(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
) -> tuple[Project, ApiKeyRecord]:
    """Extract Bearer token, verify API key, return (project, key_record)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be: Bearer <api_key>",
        )
    raw_key = authorization[7:]

    api_key_service = ApiKeyService(db)
    record = api_key_service.verify(raw_key)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )

    project_service = ProjectService(db)
    project = project_service.get_by_id(record.project_id)
    return project, record


def match_scope(granted: str, required: str) -> bool:
    """Check if a single granted scope covers the required scope."""
    if granted == "*":
        return True
    if granted == required:
        return True
    # wildcard domain: "agents:*" covers "agents:read"
    if granted.endswith(":*"):
        domain = granted[:-2]
        if required.startswith(domain + ":"):
            return True
    return False


def require_scope(scope: str) -> Callable:
    """Returns a dependency that checks if the current API key has the given scope."""

    async def _check(
        auth: tuple[Project, ApiKeyRecord] = Depends(get_current_project),
    ) -> tuple[Project, ApiKeyRecord]:
        _, key_record = auth
        granted_scopes = [s.strip() for s in key_record.scopes.split(",")]
        if not any(match_scope(g, scope) for g in granted_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope: {scope}",
            )
        return auth

    return _check
