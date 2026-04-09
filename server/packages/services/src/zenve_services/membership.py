import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zenve_db.models import UserOrgMembership


class MembershipService:
    def __init__(self, db: Session):
        self.db = db

    def add_member(self, org_id: str, user_id: str, role: str = "member") -> UserOrgMembership:
        membership = UserOrgMembership(
            id=str(uuid.uuid4()),
            user_id=user_id,
            org_id=org_id,
            role=role,
        )
        self.db.add(membership)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409, detail="User is already a member of this organization"
            ) from exc
        self.db.refresh(membership)
        return membership

    def get_membership(self, user_id: str, org_id: str) -> UserOrgMembership | None:
        return (
            self.db.query(UserOrgMembership)
            .filter(UserOrgMembership.user_id == user_id, UserOrgMembership.org_id == org_id)
            .first()
        )

    def require_membership(self, user_id: str, org_id: str) -> UserOrgMembership:
        membership = self.get_membership(user_id, org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="You are not a member of this organization")
        return membership

    def require_role(self, user_id: str, org_id: str, roles: list[str]) -> UserOrgMembership:
        membership = self.require_membership(user_id, org_id)
        if membership.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role for this action")
        return membership
