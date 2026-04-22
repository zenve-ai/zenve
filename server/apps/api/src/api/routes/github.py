from fastapi import APIRouter, Depends, HTTPException

from zenve_db.models import UserRecord
from zenve_models.project import GitHubInstallationResponse, GitHubRepo
from zenve_services import get_github_service
from zenve_services.github import GitHubService
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/github", tags=["github"])


@router.post("/installation", response_model=GitHubInstallationResponse)
def save_github_installation(
    installation_id: int,
    user: UserRecord = Depends(get_current_user),
    github_service: GitHubService = Depends(get_github_service),
):
    updated = github_service.save_installation(user, installation_id)
    return GitHubInstallationResponse(installation_id=updated.github_installation_id)


@router.get("/repos", response_model=list[GitHubRepo])
def list_github_repos(
    user: UserRecord = Depends(get_current_user),
    github_service: GitHubService = Depends(get_github_service),
):
    if not user.github_installation_id:
        raise HTTPException(status_code=422, detail="No GitHub App installation found for this user.")
    return github_service.list_repos(user.github_installation_id)
