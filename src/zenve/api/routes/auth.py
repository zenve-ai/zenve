from fastapi import APIRouter, Depends, status

from zenve.models import LoginRequest, SignupRequest, TokenResponse
from zenve.services import get_auth_service
from zenve.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def signup(body: SignupRequest, service: AuthService = Depends(get_auth_service)):
    return service.signup(body)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return service.login(body)
