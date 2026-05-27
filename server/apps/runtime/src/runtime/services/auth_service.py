from sqlalchemy.orm import Session

from runtime.db.models import UserRecord
from runtime.models.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from runtime.models.errors import AuthError, ConflictError
from runtime.utils.auth import create_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def signup(self, body: SignupRequest) -> TokenResponse:
        if self.db.query(UserRecord).filter(UserRecord.email == body.email).first():
            raise ConflictError("Email already registered")

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

        if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
            raise AuthError("Invalid email or password")

        return TokenResponse(
            access_token=create_token(user.id),
            user=UserResponse.model_validate(user),
        )
