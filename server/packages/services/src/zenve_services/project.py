import re
import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zenve_db.models import Membership, Project
from zenve_models.project import ProjectCreate, ProjectUpdate


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def conflict_detail(exc: IntegrityError) -> str:
    msg = str(exc.orig) if exc.orig is not None else str(exc)
    if "projects.slug" in msg:
        return "A project with this slug already exists"
    if "projects.name" in msg:
        return "A project with this name already exists"
    return "This project conflicts with an existing record"


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_draft(self, data: ProjectCreate, owner_user_id: str) -> Project:
        """Flush a new project + membership to the DB without committing.

        Call commit_create() to finalize, or rollback() to abort.
        """
        slug = data.slug or slugify(data.name)

        project = Project(
            id=str(uuid.uuid4()),
            name=data.name,
            slug=slug,
        )
        self.db.add(project)

        membership = Membership(
            id=str(uuid.uuid4()),
            user_id=owner_user_id,
            project_id=project.id,
            role="owner",
        )
        self.db.add(membership)

        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail=conflict_detail(exc),
            ) from exc

        return project

    def commit_create(self, project: Project) -> Project:
        """Commit the pending project creation."""
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail=conflict_detail(exc),
            ) from exc
        self.db.refresh(project)
        return project

    def rollback(self) -> None:
        """Discard any pending (unflushed or flushed) changes."""
        self.db.rollback()

    def delete(self, project_id: str) -> None:
        """Hard-delete a project record."""
        project = self.db.get(Project, project_id)
        if project:
            self.db.delete(project)
            self.db.commit()

    def get_by_id(self, project_id: str) -> Project:
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def get_by_slug(self, slug: str) -> Project:
        project = self.db.query(Project).filter(Project.slug == slug).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def get_by_id_or_slug(self, identifier: str) -> Project:
        try:
            uuid.UUID(identifier)
            return self.get_by_id(identifier)
        except ValueError:
            return self.get_by_slug(identifier)

    def list_all(self) -> list[Project]:
        return self.db.query(Project).all()

    def list_for_user(self, user_id: str) -> list[tuple[Project, str]]:
        rows = (
            self.db.query(Project, Membership.role)
            .join(Membership, Membership.project_id == Project.id)
            .filter(Membership.user_id == user_id)
            .all()
        )
        return [(project, role) for project, role in rows]

    def update(self, project_id: str, data: ProjectUpdate) -> Project:
        project = self.get_by_id(project_id)
        if data.name is not None:
            project.name = data.name
        if data.slug is not None:
            project.slug = data.slug
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail=conflict_detail(exc),
            ) from exc
        self.db.refresh(project)
        return project
