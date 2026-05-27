from fastapi import APIRouter, Depends

from runtime.db.models import UserRecord
from runtime.models.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from runtime.services import get_auth_service
from runtime.services.auth_service import AuthService
from runtime.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest, service: AuthService = Depends(get_auth_service)):
    return service.signup(body)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return service.login(body)


@router.get("/me", response_model=UserResponse)
def me(user: UserRecord = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=204)
def logout():
    return None
