from pathlib import Path

from .base import BaseIssueAdapter
from .github import GitHubIssueAdapter
from .models import (
    Comment,
    CommentCreate,
    CommentNotFoundError,
    CommentUpdate,
    GitHubIssueConfig,
    Issue,
    IssueAdapterConfigBase,
    IssueAdapterError,
    IssueCreate,
    IssueListFilter,
    IssueNotFoundError,
    IssueUpdate,
    SQLiteIssueConfig,
)
from .registry import IssueAdapterRegistry
from .sqlite import SQLiteIssueAdapter


def build_issues_adapter(
    adapter_type: str,
    workspace_path: Path,
    github_token: str,
    repo: str,
) -> BaseIssueAdapter:
    """Build an issues adapter from a type string.

    - "sqlite": DB at `~/.zenve/zenve.db`, scoped by workspace_path.
    - "github" (default): uses github_token and repo.
    """
    if adapter_type == "sqlite":
        db_path = Path.home() / ".zenve" / "zenve.db"
        workspace_id = str(workspace_path.resolve())
        return SQLiteIssueAdapter(SQLiteIssueConfig(db_path=str(db_path), workspace_id=workspace_id))
    if adapter_type == "github":
        return GitHubIssueAdapter(GitHubIssueConfig(token=github_token, repo=repo))
    raise ValueError(f"Unknown issues adapter type: {adapter_type!r}")


__all__ = [
    "BaseIssueAdapter",
    "Comment",
    "CommentCreate",
    "CommentNotFoundError",
    "CommentUpdate",
    "GitHubIssueAdapter",
    "GitHubIssueConfig",
    "Issue",
    "IssueAdapterConfigBase",
    "IssueAdapterError",
    "IssueCreate",
    "IssueListFilter",
    "IssueNotFoundError",
    "IssueAdapterRegistry",
    "IssueUpdate",
    "SQLiteIssueAdapter",
    "SQLiteIssueConfig",
    "build_issues_adapter",
]
