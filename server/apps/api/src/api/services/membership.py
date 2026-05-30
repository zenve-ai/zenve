import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.db.models import Membership
from api.models.errors import AuthError, ConflictError


class MembershipService:
    def __init__(self, db: Session):
        self.db = db

    def add_member(self, workspace_id: str, user_id: str, role: str = "member") -> Membership:
        membership = Membership(
            id=str(uuid.uuid4()),
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
        )
        self.db.add(membership)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("User is already a member of this workspace") from exc
        self.db.refresh(membership)
        return membership

    def get_membership(self, user_id: str, workspace_id: str) -> Membership | None:
        return (
            self.db.query(Membership)
            .filter(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
            .first()
        )

    def require_membership(self, user_id: str, workspace_id: str) -> Membership:
        membership = self.get_membership(user_id, workspace_id)
        if not membership:
            raise AuthError("You are not a member of this workspace")
        return membership

    def require_role(self, user_id: str, workspace_id: str, roles: list[str]) -> Membership:
        membership = self.require_membership(user_id, workspace_id)
        if membership.role not in roles:
            raise AuthError("Insufficient role for this action")
        return membership
