import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.db.models import Membership, Workspace
from api.models.errors import ConflictError, NotFoundError
from api.models.workspace import WorkspaceCreate, WorkspaceUpdate


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def conflict_detail(exc: IntegrityError) -> str:
    msg = str(exc.orig) if exc.orig is not None else str(exc)
    if "workspaces.slug" in msg:
        return "A workspace with this slug already exists"
    if "workspaces.name" in msg:
        return "A workspace with this name already exists"
    return "This workspace conflicts with an existing record"


class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db

    def create_draft(self, data: WorkspaceCreate, owner_user_id: str) -> Workspace:
        """Flush a new workspace + membership to the DB without committing.

        Call commit_create() to finalize, or rollback() to abort.
        """
        slug = data.slug or slugify(data.name)

        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=data.name,
            slug=slug,
        )
        self.db.add(workspace)

        membership = Membership(
            id=str(uuid.uuid4()),
            user_id=owner_user_id,
            workspace_id=workspace.id,
            role="owner",
        )
        self.db.add(membership)

        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(conflict_detail(exc)) from exc

        return workspace

    def commit_create(self, workspace: Workspace) -> Workspace:
        """Commit the pending workspace creation."""
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(conflict_detail(exc)) from exc
        self.db.refresh(workspace)
        return workspace

    def rollback(self) -> None:
        """Discard any pending (unflushed or flushed) changes."""
        self.db.rollback()

    def delete(self, workspace_id: str) -> None:
        """Hard-delete a workspace record."""
        workspace = self.db.get(Workspace, workspace_id)
        if workspace:
            self.db.delete(workspace)
            self.db.commit()

    def get_by_id(self, workspace_id: str) -> Workspace:
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise NotFoundError("Workspace not found")
        return workspace

    def get_by_slug(self, slug: str) -> Workspace:
        workspace = self.db.query(Workspace).filter(Workspace.slug == slug).first()
        if not workspace:
            raise NotFoundError("Workspace not found")
        return workspace

    def get_by_id_or_slug(self, identifier: str) -> Workspace:
        try:
            uuid.UUID(identifier)
            return self.get_by_id(identifier)
        except ValueError:
            return self.get_by_slug(identifier)

    def list_all(self) -> list[Workspace]:
        return self.db.query(Workspace).all()

    def list_for_user(self, user_id: str) -> list[tuple[Workspace, str]]:
        rows = (
            self.db.query(Workspace, Membership.role)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .filter(Membership.user_id == user_id)
            .all()
        )
        return [(workspace, role) for workspace, role in rows]

    def update(self, workspace_id: str, data: WorkspaceUpdate) -> Workspace:
        workspace = self.get_by_id(workspace_id)
        if data.name is not None:
            workspace.name = data.name
        if data.slug is not None:
            workspace.slug = data.slug
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(conflict_detail(exc)) from exc
        self.db.refresh(workspace)
        return workspace
