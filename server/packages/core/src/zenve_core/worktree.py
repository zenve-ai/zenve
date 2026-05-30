from __future__ import annotations

from pathlib import Path

from zenve_core.git.commit import GitError, run_git
from zenve_core.git.worktree import remove_worktree
from zenve_core.models.settings import WorkspaceSettings


def setup_worktree(
    workspace_dir: Path,
    agent_slug: str,
    run_id: str,
    workspace: WorkspaceSettings,
) -> tuple[Path, str]:
    """Create an isolated worktree branched off local default branch.

    Returns (worktree_path, branch_name).
    """
    branch = f"zenve/{agent_slug}/{run_id[:8]}"
    path = workspace_dir / "worktrees" / f"{agent_slug}-{run_id[:8]}"
    try:
        run_git(["worktree", "add", "-b", branch, str(path), workspace.default_branch], workspace_dir)
    except GitError:
        try:
            run_git(["branch", "-D", branch], workspace_dir)
        except GitError:
            pass
        run_git(["worktree", "add", "-b", branch, str(path), workspace.default_branch], workspace_dir)
    return path, branch


def cleanup_worktree(workspace_dir: Path, worktree_path: Path, branch: str) -> None:
    """Remove the worktree and its local branch.

    If the agent pushed the branch, it lives on GitHub — safe to delete locally.
    If the agent did nothing, the branch had no commits worth keeping.
    """
    try:
        remove_worktree(workspace_dir, worktree_path, branch=branch)
    except GitError:
        pass
