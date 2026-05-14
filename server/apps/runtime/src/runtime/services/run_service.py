from __future__ import annotations

import json
import logging
from pathlib import Path

from runtime.models.errors import NotFoundError
from runtime.models.run import WorkspaceRun, WorkspaceRunSummary
from runtime.services.workspace_service import AGENTS_SUBDIR, ZENVE_DIR, WorkspaceService

TRANSCRIPTS_SUBDIR = "transcripts"

logger = logging.getLogger(__name__)


class RunService:
    """Reads run records written by the CLI under `.zenve/agents/{slug}/runs/{run_id}.json`."""

    def __init__(self, workspace_service: WorkspaceService):
        self.workspace_service = workspace_service

    def runs_root(self, workspace_id: str) -> Path:
        return self.workspace_service.resolve_path(workspace_id) / ZENVE_DIR / AGENTS_SUBDIR

    def iter_run_files(self, workspace_id: str) -> list[Path]:
        root = self.runs_root(workspace_id)
        if not root.exists():
            return []
        files: list[Path] = []
        for agent_dir in (d for d in root.iterdir() if d.is_dir()):
            runs_dir = agent_dir / "runs"
            if not runs_dir.exists():
                continue
            files.extend(p for p in runs_dir.glob("*.json") if p.is_file())
        return files

    def list_grouped(self, workspace_id: str, limit: int = 50) -> list[WorkspaceRun]:
        groups: dict[str, list[WorkspaceRunSummary]] = {}
        for path in self.iter_run_files(workspace_id):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                summary = WorkspaceRunSummary.model_validate(data)
                groups.setdefault(summary.run_id, []).append(summary)
            except Exception as exc:
                logger.warning("Failed to parse run file %s: %s", path, exc)

        runs: list[WorkspaceRun] = []
        for run_id, agents in groups.items():
            started_at = min(a.started_at for a in agents)
            finished_at = max(a.finished_at for a in agents)
            status = "failed" if any(a.status == "failed" for a in agents) else "done"
            runs.append(WorkspaceRun(
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                status=status,
                agents=agents,
            ))

        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[:limit]

    def get_latest(self, workspace_id: str) -> WorkspaceRun | None:
        runs = self.list_grouped(workspace_id, limit=1)
        return runs[0] if runs else None

    def get_grouped(self, workspace_id: str, run_id: str) -> WorkspaceRun:
        agents: list[WorkspaceRunSummary] = []
        for path in self.iter_run_files(workspace_id):
            if path.stem != run_id:
                continue
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                agents.append(WorkspaceRunSummary.model_validate(data))
            except Exception as exc:
                logger.warning("Failed to parse run file %s: %s", path, exc)
        if not agents:
            raise NotFoundError(f"Run {run_id} not found in workspace {workspace_id}")
        started_at = min(a.started_at for a in agents)
        finished_at = max(a.finished_at for a in agents)
        status = "failed" if any(a.status == "failed" for a in agents) else "done"
        return WorkspaceRun(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            agents=agents,
        )

    def get_events(self, workspace_id: str, run_id: str) -> list[dict]:
        transcript_path = (
            self.workspace_service.resolve_path(workspace_id)
            / ZENVE_DIR / TRANSCRIPTS_SUBDIR / f"{run_id}.jsonl"
        )
        if not transcript_path.exists():
            return []
        events: list[dict] = []
        with transcript_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return events
