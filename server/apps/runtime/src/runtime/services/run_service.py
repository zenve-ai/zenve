from __future__ import annotations

import json
import logging

from runtime.models.errors import NotFoundError
from runtime.models.run import AgentStats, TokenUsage, WorkspaceRunDetail, WorkspaceRunSummary
from runtime.services.run_db_service import RunDbService
from runtime.services.workspace_service import ZENVE_DIR, WorkspaceService

TRANSCRIPTS_SUBDIR = "transcripts"

logger = logging.getLogger(__name__)


def build_summary(r: dict) -> WorkspaceRunSummary:
    return WorkspaceRunSummary(
        run_id=r["run_id"],
        agent=r["agent_name"] or "",
        message=r.get("message"),
        issue_id=r.get("issue_id"),
        status=r["status"],
        triggered_at=r["triggered_at"],
        started_at=r.get("started_at"),
        finished_at=r.get("finished_at"),
        duration_seconds=r.get("duration_seconds"),
        exit_code=r.get("exit_code"),
    )


def build_detail(r: dict) -> WorkspaceRunDetail:
    token_usage = None
    if r.get("token_input") is not None:
        token_usage = TokenUsage(
            input_tokens=r["token_input"] or 0,
            output_tokens=r["token_output"] or 0,
            cost_usd=r.get("token_cost_usd"),
        )
    return WorkspaceRunDetail(
        run_id=r["run_id"],
        agent=r["agent_name"] or "",
        message=r.get("message"),
        issue_id=r.get("issue_id"),
        status=r["status"],
        triggered_at=r["triggered_at"],
        started_at=r.get("started_at"),
        finished_at=r.get("finished_at"),
        duration_seconds=r.get("duration_seconds"),
        exit_code=r.get("exit_code"),
        token_usage=token_usage,
        error=r.get("error"),
    )


class RunService:
    def __init__(self, workspace_service: WorkspaceService, run_db_service: RunDbService):
        self.workspace_service = workspace_service
        self.run_db_service = run_db_service

    def list_runs(self, workspace_id: str, agent: str | None = None, limit: int = 50) -> list[WorkspaceRunSummary]:
        runs = self.run_db_service.list_runs(workspace_id, agent=agent, limit=limit)
        return [build_summary(r) for r in runs]

    def get_run(self, workspace_id: str, run_id: str) -> WorkspaceRunDetail:
        r = self.run_db_service.get_run(run_id)
        if r is None or r["workspace_id"] != workspace_id:
            raise NotFoundError(f"Run {run_id} not found in workspace {workspace_id}")
        return build_detail(r)

    def get_latest(self, workspace_id: str) -> WorkspaceRunSummary | None:
        runs = self.list_runs(workspace_id, limit=1)
        return runs[0] if runs else None

    def agent_stats(self, workspace_id: str, agent_slug: str) -> AgentStats:
        runs = self.run_db_service.list_runs(workspace_id, agent=agent_slug, limit=500)
        details = [build_detail(r) for r in runs]
        return AgentStats(
            agent=agent_slug,
            total_runs=len(details),
            completed_runs=sum(1 for d in details if d.status == "completed"),
            failed_runs=sum(1 for d in details if d.status == "failed"),
            runs=details,
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
