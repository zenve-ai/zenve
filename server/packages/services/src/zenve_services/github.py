import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from zenve_db.models import Project
from zenve_utils.github import get_repo_info


class GitHubService:
    def __init__(self, db: Session):
        self.db = db

    def connect_project(self, project: Project, installation_id: int, repo: str) -> Project:
        """Validate the GitHub App can access the repo, then persist the connection."""
        try:
            info = get_repo_info(installation_id, repo)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403, 404):
                raise HTTPException(
                    status_code=422,
                    detail=f"GitHub App cannot access repo '{repo}'. Check installation_id and repo name.",
                ) from exc
            raise HTTPException(status_code=502, detail="GitHub API error") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="GitHub API unreachable") from exc

        project.github_installation_id = installation_id
        project.github_repo = repo
        project.github_default_branch = info.get("default_branch", "main")
        self.db.commit()
        self.db.refresh(project)
        return project

    def disconnect(self, project: Project) -> Project:
        """Clear the GitHub connection fields from the project."""
        project.github_installation_id = None
        project.github_repo = None
        project.github_default_branch = None
        self.db.commit()
        self.db.refresh(project)
        return project
