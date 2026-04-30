from __future__ import annotations

from pathlib import Path

from zenve_cli.runtime.commit import GitError, run_git  # noqa: F401


def create_worktree(repo_root: Path, path: Path, branch: str, base: str) -> None:
    run_git(["fetch", "origin", base], repo_root)
    run_git(["worktree", "add", "-b", branch, str(path), f"origin/{base}"], repo_root)


def remove_worktree(repo_root: Path, path: Path) -> None:
    run_git(["worktree", "remove", "--force", str(path)], repo_root)


def commit_and_push_worktree(path: Path, message: str, branch: str) -> bool:
    """Stage all changes, commit, push. Returns True if a commit was made."""
    run_git(["add", "-A"], path)
    out = run_git(["diff", "--cached", "--name-only"], path)
    if not out.strip():
        return False
    run_git(["commit", "-m", message], path)
    run_git(["push", "origin", branch], path)
    return True
