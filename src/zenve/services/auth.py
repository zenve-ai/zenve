from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from zenve.db.models import UserRecord
from zenve.models import LoginRequest, SignupRequest, TokenResponse, UserResponse
from zenve.utils.auth import create_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def signup(self, body: SignupRequest) -> TokenResponse:
        if self.db.query(UserRecord).filter(UserRecord.email == body.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        user = UserRecord(
            email=body.email,
            name=body.name,
            password_hash=hash_password(body.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return TokenResponse(
            access_token=create_token(user.id),
            user=UserResponse.model_validate(user),
        )

    def login(self, body: LoginRequest) -> TokenResponse:
        user = self.db.query(UserRecord).filter(UserRecord.email == body.email).first()

        if (
            not user
            or not user.password_hash
            or not verify_password(body.password, user.password_hash)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        return TokenResponse(
            access_token=create_token(user.id),
            user=UserResponse.model_validate(user),
        )
