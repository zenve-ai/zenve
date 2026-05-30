from __future__ import annotations

import logging
from datetime import UTC, datetime

from runtime.db.database import session_scope
from runtime.db.models import RunRecord

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def run_to_dict(r: RunRecord) -> dict:
    return {
        "run_id": r.run_id,
        "workspace_id": r.workspace_id,
        "agent_name": r.agent_name,
        "status": r.status,
        "message": r.message,
        "issue_id": r.issue_id,
        "triggered_at": r.triggered_at,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "duration_seconds": r.duration_seconds,
        "exit_code": r.exit_code,
        "error": r.error,
        "token_input": r.token_input,
        "token_output": r.token_output,
        "token_cost_usd": r.token_cost_usd,
    }


class RunDbService:
    def create_run(
        self,
        run_id: str,
        workspace_id: str,
        agent_name: str,
        message: str,
        issue_id: int | None,
    ) -> None:
        with session_scope() as db:
            db.add(RunRecord(
                run_id=run_id,
                workspace_id=workspace_id,
                agent_name=agent_name,
                message=message,
                issue_id=issue_id,
                status="queued",
                triggered_at=utcnow_iso(),
            ))

    def set_run_running(self, run_id: str) -> None:
        with session_scope() as db:
            record = db.get(RunRecord, run_id)
            if record:
                record.status = "running"
                record.started_at = utcnow_iso()

    def set_run_finished(
        self,
        run_id: str,
        status: str,
        duration_seconds: float | None = None,
        exit_code: int | None = None,
        error: str | None = None,
        token_input: int | None = None,
        token_output: int | None = None,
        token_cost_usd: float | None = None,
    ) -> None:
        with session_scope() as db:
            record = db.get(RunRecord, run_id)
            if record:
                record.status = status
                record.finished_at = utcnow_iso()
                record.duration_seconds = duration_seconds
                record.exit_code = exit_code
                record.error = error
                record.token_input = token_input
                record.token_output = token_output
                record.token_cost_usd = token_cost_usd

    def get_run(self, run_id: str) -> dict | None:
        with session_scope() as db:
            record = db.get(RunRecord, run_id)
            return run_to_dict(record) if record else None

    def list_runs(self, workspace_id: str, agent: str | None = None, limit: int = 50) -> list[dict]:
        with session_scope() as db:
            q = db.query(RunRecord).filter_by(workspace_id=workspace_id)
            if agent:
                q = q.filter_by(agent_name=agent)
            records = q.order_by(RunRecord.triggered_at.desc()).limit(limit).all()
            return [run_to_dict(r) for r in records]
