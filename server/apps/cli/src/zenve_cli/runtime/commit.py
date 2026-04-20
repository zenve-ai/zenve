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
    out = run_git(["status", "--porcelain", ".zenve/agents"], repo_root)
    return bool(out.strip())


def commit_and_push(
    repo_root: Path,
    run_id: str,
    prefix: str = "[zenve]",
    branch: str = "main",
    summary: str = "",
) -> bool:
    """Stage agent memory + runs, commit with a zenve-prefixed message, push.

    Returns True if a commit was created, False if nothing changed.
    Never commits `.zenve/snapshot.json`.
    """
    run_git(["add", ".zenve/agents"], repo_root)

    if not has_changes(repo_root):
        return False

    title = f"{prefix} {run_id}"
    if summary:
        title = f"{title} — {summary}"

    run_git(["commit", "-m", title], repo_root)
    run_git(["push", "origin", branch], repo_root)
    return True
