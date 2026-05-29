from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from runtime.db.database import session_scope
from runtime.db.models import RunAgentRecord, RunRecord

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def agent_to_dict(a: RunAgentRecord) -> dict:
    return {
        "run_id": a.run_id,
        "agent_name": a.agent_name,
        "status": a.status,
        "skip_reason": a.skip_reason,
        "started_at": a.started_at,
        "finished_at": a.finished_at,
        "exit_code": a.exit_code,
        "error": a.error,
        "item_type": a.item_type,
        "item_number": a.item_number,
        "item_title": a.item_title,
        "duration_seconds": a.duration_seconds,
        "pipeline_from": a.pipeline_from,
        "pipeline_to": json.loads(a.pipeline_to) if a.pipeline_to else None,
        "token_input": a.token_input,
        "token_output": a.token_output,
        "token_cost_usd": a.token_cost_usd,
    }


class RunDbService:
    def create_run(self, run_id: str, workspace_id: str) -> None:
        with session_scope() as db:
            db.add(RunRecord(id=run_id, workspace_id=workspace_id, status="queued", triggered_at=utcnow_iso()))

    def set_run_running(self, run_id: str) -> None:
        with session_scope() as db:
            record = db.get(RunRecord, run_id)
            if record:
                record.status = "running"
                record.started_at = utcnow_iso()

    def set_run_finished(self, run_id: str, status: str, error: str | None = None, outcome: str | None = None) -> None:
        with session_scope() as db:
            record = db.get(RunRecord, run_id)
            if record:
                record.status = status
                record.finished_at = utcnow_iso()
                if error:
                    record.error = error
                if outcome:
                    record.outcome = outcome

    def upsert_agent(
        self,
        run_id: str,
        agent_name: str,
        status: str,
        skip_reason: str | None = None,
        exit_code: int | None = None,
        error: str | None = None,
        set_finished: bool = False,
    ) -> None:
        with session_scope() as db:
            record = db.query(RunAgentRecord).filter_by(run_id=run_id, agent_name=agent_name).first()
            if record is None:
                record = RunAgentRecord(run_id=run_id, agent_name=agent_name, started_at=utcnow_iso())
                db.add(record)
            record.status = status
            if skip_reason is not None:
                record.skip_reason = skip_reason
            if exit_code is not None:
                record.exit_code = exit_code
            if error is not None:
                record.error = error
            if set_finished:
                record.finished_at = utcnow_iso()

    def update_agent_result(
        self,
        run_id: str,
        agent_name: str,
        item_type: str | None,
        item_number: int | None,
        item_title: str | None,
        duration_seconds: float | None,
        pipeline_from: str | None,
        pipeline_to: list[str] | None,
        token_input: int | None,
        token_output: int | None,
        token_cost_usd: float | None,
    ) -> None:
        with session_scope() as db:
            record = db.query(RunAgentRecord).filter_by(run_id=run_id, agent_name=agent_name).first()
            if record is None:
                return
            record.item_type = item_type
            record.item_number = item_number
            record.item_title = item_title
            record.duration_seconds = duration_seconds
            record.pipeline_from = pipeline_from
            record.pipeline_to = json.dumps(pipeline_to) if pipeline_to is not None else None
            record.token_input = token_input
            record.token_output = token_output
            record.token_cost_usd = token_cost_usd

    def get_run(self, run_id: str) -> dict | None:
        with session_scope() as db:
            run = db.get(RunRecord, run_id)
            if run is None:
                return None
            agents = db.query(RunAgentRecord).filter_by(run_id=run_id).all()
            return {
                "run_id": run.id,
                "workspace_id": run.workspace_id,
                "status": run.status,
                "error": run.error,
                "triggered_at": run.triggered_at,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "outcome": run.outcome,
                "agents": [agent_to_dict(a) for a in agents],
            }

    def list_runs(self, workspace_id: str, limit: int = 50) -> list[dict]:
        with session_scope() as db:
            runs = (
                db.query(RunRecord)
                .filter_by(workspace_id=workspace_id)
                .order_by(RunRecord.triggered_at.desc())
                .limit(limit)
                .all()
            )
            result = []
            for run in runs:
                agents = db.query(RunAgentRecord).filter_by(run_id=run.id).all()
                result.append({
                    "run_id": run.id,
                    "workspace_id": run.workspace_id,
                    "status": run.status,
                    "error": run.error,
                    "triggered_at": run.triggered_at,
                    "started_at": run.started_at,
                    "finished_at": run.finished_at,
                    "outcome": run.outcome,
                    "agents": [agent_to_dict(a) for a in agents],
                })
            return result

    def list_agent_stats(self, workspace_id: str, agent_name: str) -> dict:
        with session_scope() as db:
            agents = (
                db.query(RunAgentRecord)
                .join(RunRecord, RunRecord.id == RunAgentRecord.run_id)
                .filter(RunRecord.workspace_id == workspace_id, RunAgentRecord.agent_name == agent_name)
                .order_by(RunRecord.triggered_at.desc())
                .all()
            )
            completed = sum(1 for a in agents if a.status == "completed")
            failed = sum(1 for a in agents if a.status == "failed")
            return {
                "agent": agent_name,
                "total_runs": len(agents),
                "completed_runs": completed,
                "failed_runs": failed,
                "runs": [agent_to_dict(a) for a in agents],
            }
