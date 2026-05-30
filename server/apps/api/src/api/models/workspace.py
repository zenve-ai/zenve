from datetime import datetime

from pydantic import BaseModel

from api.models.api_key import ApiKeyCreated


class WorkspaceCreate(BaseModel):
    name: str
    slug: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    github_installation_id: int | None = None
    github_repo: str | None = None
    github_default_branch: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceWithRoleResponse(WorkspaceResponse):
    role: str


class WorkspaceCreatedResponse(WorkspaceResponse):
    api_key: ApiKeyCreated
    role: str = "owner"


class WorkspaceGitHubConnect(BaseModel):
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


class InitAgentSpec(BaseModel):
    name: str
    template: str | None = None


class WorkspaceInit(BaseModel):
    description: str | None = None
    agents: list[InitAgentSpec] = []
