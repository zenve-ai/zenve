from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from zenve_cli.core.config import zenve_dir
from zenve_cli.github.client import GitHubClient
from zenve_cli.models.snapshot import Snapshot, SnapshotIssue, SnapshotPR

SNAPSHOT_FILE = "snapshot.json"


def label_names(labels: list[dict]) -> list[str]:
    return [lbl.get("name", "") for lbl in labels if isinstance(lbl, dict)]


def assignee_logins(assignees: list[dict]) -> list[str]:
    return [a.get("login", "") for a in assignees if isinstance(a, dict)]


def build_snapshot(client: GitHubClient, run_id: str) -> Snapshot:
    issues_raw = client.list_open_issues()
    pulls_raw = client.list_open_pulls()
    branches = client.list_branches()

    issues = [
        SnapshotIssue(
            number=raw.get("number", 0),
            title=raw.get("title", ""),
            body=raw.get("body") or "",
            labels=label_names(raw.get("labels", [])),
            assignees=assignee_logins(raw.get("assignees", [])),
            state=raw.get("state", "open"),
            created_at=raw.get("created_at", "") or "",
        )
        for raw in issues_raw
    ]

    pulls = [
        SnapshotPR(
            number=raw.get("number", 0),
            title=raw.get("title", ""),
            body=raw.get("body") or "",
            labels=label_names(raw.get("labels", [])),
            assignees=assignee_logins(raw.get("assignees", [])),
            state=raw.get("state", "open"),
            head=(raw.get("head") or {}).get("ref", ""),
            base=(raw.get("base") or {}).get("ref", ""),
            draft=bool(raw.get("draft", False)),
            created_at=raw.get("created_at", "") or "",
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
