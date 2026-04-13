from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from zenve_db.models import Agent, Run


class RunService:
    def __init__(self, db: Session):
        self.db = db

    def create_run(
        self,
        org_id: str,
        agent_id: str,
        trigger: str,
        adapter_type: str,
        message: str | None = None,
        session_id: str | None = None,
        status: str = "queued",
    ) -> Run:
        run = Run(
            org_id=org_id,
            agent_id=agent_id,
            trigger=trigger,
            status=status,
            adapter_type=adapter_type,
            message=message,
            session_id=session_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_id(self, org_id: str, run_id: str) -> Run:
        run = self.db.get(Run, run_id)
        if not run or run.org_id != org_id:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    def list_runs(
        self,
        org_id: str,
        agent_id: str | None = None,
        status: str | None = None,
        trigger: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[Run]:
        q = self.db.query(Run).filter(Run.org_id == org_id)
        if agent_id:
            q = q.filter(Run.agent_id == agent_id)
        if status:
            q = q.filter(Run.status == status)
        if trigger:
            q = q.filter(Run.trigger == trigger)
        if session_id:
            q = q.filter(Run.session_id == session_id)
        return q.order_by(Run.created_at.desc()).limit(limit).all()

    def list_sessions(
        self,
        org_id: str,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Return sessions grouped with their runs.

        Returns a list of dicts: {session_id, agent_id, agent_slug, runs}.
        """
        q = self.db.query(Run).filter(
            Run.org_id == org_id,
            Run.session_id.isnot(None),
        )
        if agent_id:
            q = q.filter(Run.agent_id == agent_id)
        runs = q.order_by(Run.created_at.desc()).all()

        sessions: dict[str, dict] = {}
        for run in runs:
            sid = run.session_id
            if sid not in sessions:
                sessions[sid] = {
                    "session_id": sid,
                    "agent_id": run.agent_id,
                    "agent_slug": run.agent.slug if run.agent else "",
                    "runs": [],
                }
            sessions[sid]["runs"].append(run)

        result = list(sessions.values())[:limit]
        return result

    def update(self, run_id: str, **kwargs) -> Run:
        run = self.db.get(Run, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        for key, value in kwargs.items():
            setattr(run, key, value)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_transcript(self, run: Run) -> str | None:
        if not run.transcript_path:
            return None
        path = Path(run.transcript_path)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def has_active_run(self, agent_id: str) -> bool:
        return (
            self.db.query(Run)
            .filter(Run.agent_id == agent_id, Run.status.in_(["queued", "running"]))
            .first()
            is not None
        )

    def cancel_run(self, run: Run) -> Run:
        if run.status not in ("queued", "running"):
            raise HTTPException(
                status_code=409,
                detail=f"Run cannot be cancelled (status: {run.status})",
            )
        run.status = "cancelled"
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_agent_for_run(self, org_id: str, identifier: str) -> Agent:
        try:
            uuid.UUID(identifier)
            filter_col = Agent.id
        except ValueError:
            filter_col = Agent.slug
        agent = (
            self.db.query(Agent)
            .filter(filter_col == identifier, Agent.org_id == org_id, Agent.status != "archived")
            .first()
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
