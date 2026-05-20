from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from zenve_engine.config import zenve_dir
from zenve_engine.constants import SNAPSHOT_FILE
from zenve_engine.github.client import GitHubClient
from zenve_engine.models.snapshot import Snapshot, SnapshotComment, SnapshotIssue, SnapshotPR
from zenve_issues import BaseIssueAdapter, IssueListFilter


def assignee_logins(assignees: list[dict]) -> list[str]:
    return [a.get("login", "") for a in assignees if isinstance(a, dict)]


def build_snapshot(issues_adapter: BaseIssueAdapter, gh: GitHubClient, run_id: str) -> Snapshot:
    issues_raw = issues_adapter.list(IssueListFilter(state="open"))
    pulls_raw = gh.list_open_pulls()
    branches = gh.list_branches()

    issues = [
        SnapshotIssue(
            number=issue.id,
            title=issue.title,
            body=issue.body,
            labels=issue.labels,
            assignees=issue.assignees,
            state=issue.state,
            created_at=issue.created_at,
            comments=[
                SnapshotComment(author=c.author, body=c.body, created_at=c.created_at)
                for c in issues_adapter.list_comments(issue.id)
            ],
        )
        for issue in issues_raw
    ]

    pulls = [
        SnapshotPR(
            number=raw.get("number", 0),
            title=raw.get("title", ""),
            body=raw.get("body") or "",
            labels=[lbl.get("name", "") for lbl in raw.get("labels", []) if isinstance(lbl, dict)],
            assignees=assignee_logins(raw.get("assignees", [])),
            state=raw.get("state", "open"),
            head=(raw.get("head") or {}).get("ref", ""),
            base=(raw.get("base") or {}).get("ref", ""),
            draft=bool(raw.get("draft", False)),
            created_at=raw.get("created_at", "") or "",
            comments=[
                SnapshotComment(
                    author=c["user"]["login"],
                    body=c["body"],
                    created_at=c["created_at"],
                )
                for c in gh.get_comments(raw["number"])
            ],
        )
        for raw in pulls_raw
    ]

    return Snapshot(
        fetched_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        run_id=run_id,
        issues=issues,
        pull_requests=pulls,
        branches=branches,
    )


def write_snapshot(repo_root: Path, snapshot: Snapshot) -> Path:
    path = zenve_dir(repo_root) / SNAPSHOT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_snapshot(repo_root: Path) -> Snapshot | None:
    path = zenve_dir(repo_root) / SNAPSHOT_FILE
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Snapshot.model_validate(raw)
