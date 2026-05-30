import uuid
from datetime import datetime

from sqlalchemy import Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from runtime.db.database import Base


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(nullable=True)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class RunRecord(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column("id", String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    message: Mapped[str | None] = mapped_column(nullable=True)
    issue_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triggered_at: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)
    token_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_cost_usd: Mapped[float | None] = mapped_column(nullable=True)

    __table_args__ = (Index("ix_runs_workspace_triggered", "workspace_id", "triggered_at"),)
