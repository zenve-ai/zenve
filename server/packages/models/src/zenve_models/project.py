from datetime import datetime

from pydantic import BaseModel

from zenve_models.api_key import ApiKeyCreated


class ProjectCreate(BaseModel):
    name: str
    slug: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    github_installation_id: int | None = None
    github_repo: str | None = None
    github_default_branch: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectWithRoleResponse(ProjectResponse):
    role: str


class ProjectCreatedResponse(ProjectResponse):
    api_key: ApiKeyCreated
    role: str = "owner"


class ProjectGitHubConnect(BaseModel):
    installation_id: int | None = None
    repo: str  # format: owner/name


class GitHubRepo(BaseModel):
    id: int
    full_name: str  # "owner/name"
    name: str
    private: bool
    default_branch: str


class GitHubInstallationResponse(BaseModel):
    installation_id: int
