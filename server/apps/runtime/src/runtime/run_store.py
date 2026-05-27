from __future__ import annotations

import queue
import threading
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
        self._subscribers: dict[str, list[queue.Queue]] = {}
        # Per-run event replay buffer — kept for the lifetime of an active run so
        # reconnecting clients (e.g. the UI panel closed and reopened) receive the
        # full event history from the stream rather than only future events.
        self._event_buffer: dict[str, list[dict]] = {}
        self._lock = threading.Lock()

    def create(self, run_id: str, workspace_id: str) -> RunRecord:
        record = RunRecord(run_id=run_id, workspace_id=workspace_id, status="queued")
        with self._lock:
            self._runs[run_id] = record
            self._subscribers[run_id] = []
            self._event_buffer[run_id] = []
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

    def subscribe(self, run_id: str) -> queue.Queue:
        """Return a queue pre-populated with all buffered events, then live ones.

        Holding the lock while both copying the buffer and appending to the
        subscriber list ensures no event can slip between the two steps.
        """
        q: queue.Queue = queue.Queue()
        with self._lock:
            for event in self._event_buffer.get(run_id, []):
                q.put(event)
            if run_id not in self._subscribers:
                self._subscribers[run_id] = []
            self._subscribers[run_id].append(q)
        return q

    def unsubscribe(self, run_id: str, q: queue.Queue) -> None:
        with self._lock:
            if run_id in self._subscribers:
                try:
                    self._subscribers[run_id].remove(q)
                except ValueError:
                    pass

    def broadcast(self, run_id: str, event: dict) -> None:
        with self._lock:
            self._event_buffer.setdefault(run_id, []).append(event)
            for q in self._subscribers.get(run_id, []):
                q.put(event)

    def close(self, run_id: str) -> None:
        with self._lock:
            for q in self._subscribers.get(run_id, []):
                q.put(None)
            self._subscribers.pop(run_id, None)
            self._event_buffer.pop(run_id, None)
