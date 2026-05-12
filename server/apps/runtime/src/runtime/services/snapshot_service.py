from pathlib import Path
from uuid import uuid4

import zenve_engine
from runtime.models.errors import ExternalError, ValidationError
from runtime.models.snapshot import SnapshotResponse
from runtime.services.workspace_service import WorkspaceService
from zenve_engine.env import resolve_github_token


class SnapshotService:
    def __init__(self, workspace_service: WorkspaceService) -> None:
        self.workspace_service = workspace_service

    def take(self, workspace_id: str) -> SnapshotResponse:
        detail = self.workspace_service.detail(workspace_id)
        github_token = resolve_github_token()
        if not github_token:
            raise ExternalError("No GitHub token. Set ZENVE_GH_TOKEN or run `gh auth login`.")

        if not detail.repo:
            raise ValidationError(
                f"Could not detect GitHub remote origin for workspace at {detail.path}"
            )

        run_id = uuid4().hex
        snap = zenve_engine.snapshot(
            project_dir=Path(detail.path),
            run_id=run_id,
            github_token=github_token,
            repo=detail.repo,
        )
        return SnapshotResponse(
            run_id=snap.run_id,
            fetched_at=snap.fetched_at,
            issues_count=len(snap.issues),
            pull_requests_count=len(snap.pull_requests),
            branches_count=len(snap.branches),
        )
