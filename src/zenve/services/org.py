import re
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zenve.config.settings import settings
from zenve.db.models import Organization
from zenve.models.org import OrgCreate, OrgUpdate


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _conflict_detail(exc: IntegrityError) -> str:
    msg = str(exc.orig) if exc.orig is not None else str(exc)
    if "organizations.slug" in msg:
        return "An organization with this slug already exists"
    if "organizations.name" in msg:
        return "An organization with this name already exists"
    return "This organization conflicts with an existing record"


class OrgService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: OrgCreate) -> Organization:
        slug = data.slug or _slugify(data.name)
        base_path = str(Path(settings.data_dir) / "orgs" / slug)

        org = Organization(
            id=str(uuid.uuid4()),
            name=data.name,
            slug=slug,
            base_path=base_path,
        )
        self.db.add(org)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail=_conflict_detail(exc),
            ) from exc
        self.db.refresh(org)

        Path(base_path).mkdir(parents=True, exist_ok=True)

        return org

    def get_by_id(self, org_id: str) -> Organization:
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org

    def get_by_slug(self, slug: str) -> Organization:
        org = self.db.query(Organization).filter(Organization.slug == slug).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org

    def get_by_id_or_slug(self, identifier: str) -> Organization:
        try:
            uuid.UUID(identifier)
            return self.get_by_id(identifier)
        except ValueError:
            return self.get_by_slug(identifier)

    def list_all(self) -> list[Organization]:
        return self.db.query(Organization).all()

    def update(self, org_id: str, data: OrgUpdate) -> Organization:
        org = self.get_by_id(org_id)
        if data.name is not None:
            org.name = data.name
        if data.slug is not None:
            org.slug = data.slug
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail=_conflict_detail(exc),
            ) from exc
        self.db.refresh(org)
        return org
