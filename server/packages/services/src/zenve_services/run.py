from __future__ import annotations

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
        status: str = "queued",
    ) -> Run:
        run = Run(
            org_id=org_id,
            agent_id=agent_id,
            trigger=trigger,
            status=status,
            adapter_type=adapter_type,
            message=message,
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
        limit: int = 50,
    ) -> list[Run]:
        q = self.db.query(Run).filter(Run.org_id == org_id)
        if agent_id:
            q = q.filter(Run.agent_id == agent_id)
        if status:
            q = q.filter(Run.status == status)
        if trigger:
            q = q.filter(Run.trigger == trigger)
        return q.order_by(Run.created_at.desc()).limit(limit).all()

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

    def get_agent_for_run(self, org_id: str, agent_id: str) -> Agent:
        agent = (
            self.db.query(Agent)
            .filter(Agent.id == agent_id, Agent.org_id == org_id, Agent.status != "archived")
            .first()
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
