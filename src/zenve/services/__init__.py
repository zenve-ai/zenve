from fastapi import Depends
from sqlalchemy.orm import Session

from zenve.db.database import get_db
from zenve.services.auth import AuthService


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)
