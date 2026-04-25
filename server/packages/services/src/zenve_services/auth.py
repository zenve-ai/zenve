import secrets

import httpx
from sqlalchemy.orm import Session

from zenve_config.settings import get_settings
from zenve_db.models import UserRecord
from zenve_models import LoginRequest, SignupRequest, TokenResponse, UserResponse
from zenve_models.errors import AuthError, ConflictError
from zenve_utils.auth import create_token, hash_password, verify_password

_oauth_states: set[str] = set()


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

        if (
            not user
            or not user.password_hash
            or not verify_password(body.password, user.password_hash)
        ):
            raise AuthError("Invalid email or password")

        return TokenResponse(
            access_token=create_token(user.id),
            user=UserResponse.model_validate(user),
        )

    def create_oauth_state(self) -> str:
        state = secrets.token_urlsafe(32)
        _oauth_states.add(state)
        return state

    def github_oauth_callback(self, code: str, state: str) -> UserRecord:
        if state not in _oauth_states:
            raise ValueError("Invalid or expired OAuth state")
        _oauth_states.discard(state)

        settings = get_settings()

        token_resp = httpx.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_app_client_id,
                "client_secret": settings.github_app_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Failed to obtain GitHub access token")

        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        user_resp = httpx.get("https://api.github.com/user", headers=gh_headers, timeout=10)
        gh_user = user_resp.json()

        email: str | None = gh_user.get("email")
        if not email:
            emails_resp = httpx.get(
                "https://api.github.com/user/emails", headers=gh_headers, timeout=10
            )
            for entry in emails_resp.json():
                if entry.get("primary") and entry.get("verified"):
                    email = entry["email"]
                    break

        if not email:
            raise ValueError("Could not retrieve a verified email from GitHub")

        user = self.db.query(UserRecord).filter(UserRecord.email == email).first()
        if not user:
            user = UserRecord(
                email=email,
                name=gh_user.get("name") or gh_user.get("login") or email,
                avatar_url=gh_user.get("avatar_url"),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        return user
