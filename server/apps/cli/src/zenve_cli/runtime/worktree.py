from __future__ import annotations

import fnmatch
from pathlib import Path

from zenve_cli.runtime.commit import GitError, run_git  # noqa: F401


def create_worktree(repo_root: Path, path: Path, branch: str, base: str) -> None:
    run_git(["fetch", "origin", base], repo_root)
    run_git(["worktree", "add", "-b", branch, str(path), f"origin/{base}"], repo_root)


def create_readonly_worktree(repo_root: Path, path: Path, branch: str) -> None:
    """Create a detached-HEAD worktree at the tip of an existing remote branch.

    Used by review_pr agents — the agent can read the PR's code but no new
    branch is created and nothing is committed or pushed.
    """
    run_git(["fetch", "origin", branch], repo_root)
    run_git(["worktree", "add", "--detach", str(path), f"origin/{branch}"], repo_root)


def create_writable_worktree(repo_root: Path, path: Path, branch: str) -> None:
    run_git(["fetch", "origin", branch], repo_root)
    run_git(["worktree", "add", "-B", branch, str(path), f"origin/{branch}"], repo_root)


def remove_worktree(repo_root: Path, path: Path) -> None:
    run_git(["worktree", "remove", "--force", str(path)], repo_root)


def stage_changes(path: Path) -> list[str]:
    """Stage all changes; return list of changed file paths (empty if nothing to commit)."""
    run_git(["add", "-A"], path)
    out = run_git(["diff", "--cached", "--name-only"], path)
    return [ln for ln in out.splitlines() if ln.strip()]


def commit_and_push(path: Path, message: str, branch: str) -> None:
    run_git(["commit", "-m", message], path)
    run_git(["push", "origin", branch], path)


def paths_within(changed: list[str], allowed: list[str]) -> bool:
    """Return True if every changed path matches at least one allowed glob.

    Uses fnmatch shell-style globs — `*` matches anything including `/`, so
    `docs/*` matches both `docs/x.md` and `docs/sub/x.md`. `docs/**` is
    equivalent. Patterns are matched against POSIX-style relative paths.
    """
    return all(any(fnmatch.fnmatch(p, pat) for pat in allowed) for p in changed)
