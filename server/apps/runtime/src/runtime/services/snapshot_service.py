from pathlib import Path
from uuid import uuid4

import zenve_engine
from runtime.models.errors import ExternalError, ValidationError
from runtime.models.snapshot import SnapshotResponse
from runtime.services.workspace_service import WorkspaceService
from zenve_engine.config import load_project_settings
from zenve_engine.env import resolve_github_token


class SnapshotService:
    def __init__(self, workspace_service: WorkspaceService, issues_adapter_type: str = "github") -> None:
        self.workspace_service = workspace_service
        self.issues_adapter_type = issues_adapter_type

    def take(self, workspace_id: str) -> SnapshotResponse:
        detail = self.workspace_service.detail(workspace_id)
        github_token = resolve_github_token()
        if not github_token:
            raise ExternalError("No GitHub token. Set ZENVE_GH_TOKEN or run `gh auth login`.")

        if not detail.repo:
            raise ValidationError(
                f"Could not detect GitHub remote origin for workspace at {detail.path}"
            )

        project_dir = Path(detail.path)
        project = load_project_settings(project_dir)
        adapter_type = project.issues.adapter or self.issues_adapter_type

        run_id = uuid4().hex
        snap = zenve_engine.snapshot(
            project_dir=project_dir,
            run_id=run_id,
            github_token=github_token,
            repo=detail.repo,
            issues_adapter_type=adapter_type,
        )
        return SnapshotResponse(
            run_id=snap.run_id,
            fetched_at=snap.fetched_at,
            issues_count=len(snap.issues),
            pull_requests_count=len(snap.pull_requests),
            branches_count=len(snap.branches),
        )
