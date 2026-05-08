from __future__ import annotations

import json
import logging
from pathlib import Path

from zenve_models.errors import NotFoundError
from zenve_models.run import WorkspaceRunDetail, WorkspaceRunSummary

from zenve_services.workspace_service import AGENTS_SUBDIR, ZENVE_DIR, WorkspaceService

logger = logging.getLogger(__name__)


class RunService:
    """Reads run records written by the CLI under `.zenve/agents/{slug}/runs/{run_id}.json`."""

    def __init__(self, workspace_service: WorkspaceService):
        self.workspace_service = workspace_service

    def runs_root(self, workspace_id: str) -> Path:
        return self.workspace_service.resolve_path(workspace_id) / ZENVE_DIR / AGENTS_SUBDIR

    def iter_run_files(self, workspace_id: str, agent: str | None) -> list[Path]:
        root = self.runs_root(workspace_id)
        if not root.exists():
            return []
        agent_dirs = [root / agent] if agent else [d for d in root.iterdir() if d.is_dir()]
        files: list[Path] = []
        for agent_dir in agent_dirs:
            runs_dir = agent_dir / "runs"
            if not runs_dir.exists():
                continue
            files.extend(p for p in runs_dir.glob("*.json") if p.is_file())
        return files

    def list_for_workspace(
        self, workspace_id: str, agent: str | None = None, limit: int = 50
    ) -> list[WorkspaceRunSummary]:
        summaries: list[WorkspaceRunSummary] = []
        for path in self.iter_run_files(workspace_id, agent):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                summaries.append(WorkspaceRunSummary.model_validate(data))
            except Exception as exc:
                logger.warning("Failed to parse run file %s: %s", path, exc)
        summaries.sort(key=lambda s: s.started_at, reverse=True)
        return summaries[:limit]

    def get(self, workspace_id: str, run_id: str) -> WorkspaceRunDetail:
        for path in self.iter_run_files(workspace_id, agent=None):
            if path.stem == run_id:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                return WorkspaceRunDetail.model_validate(data)
        raise NotFoundError(f"Run {run_id} not found in workspace {workspace_id}")
