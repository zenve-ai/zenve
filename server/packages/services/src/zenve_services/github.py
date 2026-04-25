import httpx
from sqlalchemy.orm import Session

from zenve_db.models import Project, UserRecord
from zenve_models.errors import ExternalError, ValidationError
from zenve_models.project import GitHubRepo
from zenve_utils.github import get_repo_info, list_installation_repos


class GitHubService:
    def __init__(self, db: Session):
        self.db = db

    def connect_project(self, project: Project, installation_id: int, repo: str) -> Project:
        """Validate the GitHub App can access the repo, then persist the connection."""
        try:
            info = get_repo_info(installation_id, repo)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403, 404):
                raise ValidationError(
                    f"GitHub App cannot access repo '{repo}'. Check installation_id and repo name."
                ) from exc
            raise ExternalError("GitHub API error") from exc
        except Exception as exc:
            raise ExternalError("GitHub API unreachable") from exc

        project.github_installation_id = installation_id
        project.github_repo = repo
        project.github_default_branch = info.get("default_branch", "main")
        self.db.commit()
        self.db.refresh(project)
        return project

    def save_installation(self, user: UserRecord, installation_id: int) -> UserRecord:
        """Persist the GitHub App installation_id on the user record."""
        user.github_installation_id = installation_id
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_repos(self, installation_id: int) -> list[GitHubRepo]:
        try:
            raw = list_installation_repos(installation_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403, 404):
                raise ValidationError("GitHub App installation not found or access denied.") from exc
            raise ExternalError("GitHub API error") from exc
        except RuntimeError as exc:
            raise ExternalError(str(exc)) from exc
        except Exception as exc:
            raise ExternalError("GitHub API unreachable") from exc
        return [
            GitHubRepo(
                id=r["id"],
                full_name=r["full_name"],
                name=r["name"],
                private=r["private"],
                default_branch=r["default_branch"],
            )
            for r in raw
        ]

    def disconnect(self, project: Project) -> Project:
        """Clear the GitHub connection fields from the project."""
        project.github_installation_id = None
        project.github_repo = None
        project.github_default_branch = None
        self.db.commit()
        self.db.refresh(project)
        return project
