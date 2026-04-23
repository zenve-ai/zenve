from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from zenve_config.settings import Settings, get_settings
from zenve_db.models import UserRecord
from zenve_models import LoginRequest, SignupRequest, TokenResponse, UserResponse
from zenve_services import get_auth_service
from zenve_services.auth import AuthService
from zenve_utils.auth import create_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
def me(current_user: UserRecord = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, service: AuthService = Depends(get_auth_service)):
    return service.signup(body)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return service.login(body)


@router.get("/github")
def github_oauth_start(
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
):
    if not settings.github_app_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    state = service.create_oauth_state()
    params = {
        "client_id": settings.github_app_client_id,
        "scope": "user:email",
        "state": state,
    }
    url = "https://github.com/login/oauth/authorize?" + urlencode(params)
    return RedirectResponse(url=url, status_code=302)


@router.get("/github/callback")
def github_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    try:
        user = service.github_oauth_callback(code, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    user_data = UserResponse.model_validate(user)
    access_token = create_token(user.id)
    if settings.github_frontend_redirect_uri:
        redirect_url = f"{settings.github_frontend_redirect_uri.rstrip('/')}?token={access_token}"
        return RedirectResponse(url=redirect_url, status_code=302)
    return TokenResponse(user=user_data, access_token=access_token)
