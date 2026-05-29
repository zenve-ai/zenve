from __future__ import annotations

import json
import logging

from runtime.models.errors import NotFoundError
from runtime.models.run import (
    PipelineTransition,
    RunItem,
    TokenUsage,
    WorkspaceRun,
    WorkspaceRunDetail,
    WorkspaceRunSummary,
)
from runtime.services.run_db_service import RunDbService
from runtime.services.workspace_service import ZENVE_DIR, WorkspaceService

TRANSCRIPTS_SUBDIR = "transcripts"

logger = logging.getLogger(__name__)


def build_summary(agent_dict: dict) -> WorkspaceRunSummary:
    return WorkspaceRunSummary(
        run_id=agent_dict["run_id"] if "run_id" in agent_dict else "",
        agent=agent_dict["agent_name"],
        started_at=agent_dict["started_at"] or "",
        finished_at=agent_dict["finished_at"] or "",
        duration_seconds=agent_dict["duration_seconds"] or 0.0,
        status=agent_dict["status"],
        exit_code=agent_dict["exit_code"] or 0,
    )


def build_detail(agent_dict: dict, run_id: str) -> WorkspaceRunDetail:
    item = None
    if agent_dict.get("item_number") is not None:
        item = RunItem(
            type=agent_dict["item_type"] or "issue",
            number=agent_dict["item_number"],
            title=agent_dict["item_title"] or "",
        )
    token_usage = None
    if agent_dict.get("token_input") is not None:
        token_usage = TokenUsage(
            input_tokens=agent_dict["token_input"] or 0,
            output_tokens=agent_dict["token_output"] or 0,
            cost_usd=agent_dict["token_cost_usd"],
        )
    pipeline_transition = None
    if agent_dict.get("pipeline_from") is not None:
        raw_to = agent_dict.get("pipeline_to")
        to_label = raw_to if isinstance(raw_to, list) else (json.loads(raw_to) if isinstance(raw_to, str) else None)
        pipeline_transition = PipelineTransition(
            from_label=agent_dict["pipeline_from"],
            to_label=to_label,
        )
    return WorkspaceRunDetail(
        run_id=run_id,
        agent=agent_dict["agent_name"],
        started_at=agent_dict["started_at"] or "",
        finished_at=agent_dict["finished_at"] or "",
        duration_seconds=agent_dict["duration_seconds"] or 0.0,
        status=agent_dict["status"],
        exit_code=agent_dict["exit_code"] or 0,
        item=item,
        token_usage=token_usage,
        pipeline_transition=pipeline_transition,
        error=agent_dict.get("error"),
    )


class RunService:
    def __init__(self, workspace_service: WorkspaceService, run_db_service: RunDbService):
        self.workspace_service = workspace_service
        self.run_db_service = run_db_service

    def list_grouped(self, workspace_id: str, limit: int = 50) -> list[WorkspaceRun]:
        runs = self.run_db_service.list_runs(workspace_id, limit=limit)
        result = []
        for r in runs:
            agents = [build_summary({**a, "run_id": r["run_id"]}) for a in r["agents"]]
            started = r["started_at"] or r["triggered_at"]
            finished = r["finished_at"] or r["started_at"] or r["triggered_at"]
            result.append(WorkspaceRun(
                run_id=r["run_id"],
                started_at=started,
                finished_at=finished,
                status=r["status"],
                error=r.get("error"),
                agents=agents,
            ))
        return result

    def get_latest(self, workspace_id: str) -> WorkspaceRun | None:
        runs = self.list_grouped(workspace_id, limit=1)
        return runs[0] if runs else None

    def get_grouped(self, workspace_id: str, run_id: str) -> WorkspaceRun:
        r = self.run_db_service.get_run(run_id)
        if r is None or r["workspace_id"] != workspace_id:
            raise NotFoundError(f"Run {run_id} not found in workspace {workspace_id}")
        agents = [build_summary({**a, "run_id": run_id}) for a in r["agents"]]
        started = r["started_at"] or r["triggered_at"]
        finished = r["finished_at"] or r["started_at"] or r["triggered_at"]
        return WorkspaceRun(
            run_id=run_id,
            started_at=started,
            finished_at=finished,
            status=r["status"],
            error=r.get("error"),
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
