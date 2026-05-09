from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def run_git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def has_changes(repo_root: Path) -> bool:
    out = run_git(["status", "--porcelain", ".zenve"], repo_root)
    return bool(out.strip())


def has_dirty_zenve(repo_root: Path) -> bool:
    """Return True if `.zenve/` has uncommitted changes (staged or unstaged)."""
    out = run_git(["status", "--porcelain", "--", ".zenve"], repo_root)
    return bool(out.strip())


def has_dirty_outside_zenve(repo_root: Path) -> bool:
    """Return True if any uncommitted change exists outside `.zenve/`."""
    out = run_git(["status", "--porcelain", "--", ":(exclude).zenve", "."], repo_root)
    return bool(out.strip())


def fetch_origin(repo_root: Path) -> None:
    """Fetch all refs from origin."""
    run_git(["fetch", "origin"], repo_root)


def reset_to_remote(repo_root: Path, branch: str = "main") -> None:
    """Fast-forward the local checkout to origin/{branch} after an artifact PR merges.

    Deliberately omits `git clean -fd` — untracked run-result JSON files of in-flight
    parallel agents would be wiped. `reset --hard` alone makes merged content visible.
    """
    run_git(["fetch", "origin", branch], repo_root)
    run_git(["reset", "--hard", f"origin/{branch}"], repo_root)


def remote_branch_exists(repo_root: Path, branch: str) -> bool:
    """Return True if origin/{branch} exists after fetch."""
    try:
        run_git(["rev-parse", "--verify", f"origin/{branch}"], repo_root)
        return True
    except GitError:
        return False


def commit_skills(repo_root: Path, message: str, branch: str = "main") -> bool:
    """Stage .agents/skills/ and .claude/skills/, commit, and push. Returns True if a commit was made."""
    paths_to_add = []
    for p in [".agents/skills", ".claude/skills"]:
        if (repo_root / p).exists():
            paths_to_add.append(p)
    if not paths_to_add:
        return False
    run_git(["add", *paths_to_add], repo_root)
    out = run_git(["diff", "--cached", "--name-only"], repo_root)
    if not out.strip():
        return False
    run_git(["commit", "-m", message], repo_root)
    run_git(["push", "origin", branch], repo_root)
    return True


def commit_zenve_dir(repo_root: Path, message: str, branch: str = "main") -> bool:
    """Stage .zenve/, commit, and push. Returns True if a commit was made."""
    run_git(["add", ".zenve"], repo_root)
    out = run_git(["diff", "--cached", "--name-only"], repo_root)
    if not out.strip():
        return False
    run_git(["commit", "-m", message], repo_root)
    run_git(["push", "origin", branch], repo_root)
    return True


def commit_agents(
    repo_root: Path,
    run_id: str,
    prefix: str = "[zenve]",
    branch: str = "main",
    summary: str = "",
) -> bool:
    """Stage the full .zenve/ dir, commit with a zenve-prefixed message, push.

    Returns True if a commit was created, False if nothing changed.
    """
    run_git(["add", ".zenve"], repo_root)

    if not has_changes(repo_root):
        return False

    title = f"{prefix} {run_id}"
    if summary:
        title = f"{title} — {summary}"

    run_git(["commit", "-m", title], repo_root)
    run_git(["push", "origin", branch], repo_root)
    return True
