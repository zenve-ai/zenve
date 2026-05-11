from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RunStatus = Literal["queued", "running", "done", "failed"]


@dataclass
class RunRecord:
    run_id: str
    workspace_id: str
    status: RunStatus


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(self, run_id: str, workspace_id: str) -> RunRecord:
        record = RunRecord(run_id=run_id, workspace_id=workspace_id, status="queued")
        self._runs[run_id] = record
        return record

    def update_status(self, run_id: str, status: RunStatus) -> None:
        if run_id in self._runs:
            self._runs[run_id].status = status

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list(self) -> list[RunRecord]:
        return list(self._runs.values())

    def get_active_for_workspace(self, workspace_id: str) -> RunRecord | None:
        for record in self._runs.values():
            if record.workspace_id == workspace_id and record.status in ("queued", "running"):
                return record
        return None
