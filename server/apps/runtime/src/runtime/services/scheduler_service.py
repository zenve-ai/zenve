from __future__ import annotations

import logging
import threading
from datetime import datetime

from croniter import croniter

from runtime.models.run import RunTriggerRequest
from runtime.run_store import RunStore
from runtime.services.run_trigger_service import RunTriggerService
from runtime.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


def scheduled_now(schedule: str) -> bool:
    now = datetime.now()
    prev = croniter(schedule, now).get_prev(datetime)
    return (now - prev).total_seconds() <= 10


class SchedulerService:
    def __init__(
        self, workspace_service: WorkspaceService, trigger_service: RunTriggerService, run_store: RunStore
    ) -> None:
        self.workspace_service = workspace_service
        self.trigger_service = trigger_service
        self.run_store = run_store
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        logger.info("SchedulerService started")

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("SchedulerService stopped")

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("SchedulerService tick error")
            self._stop.wait(timeout=10)

    def _tick(self) -> None:
        logger.info("Tick from SchedulerService")
        for ws in self.workspace_service.list():
            try:
                detail = self.workspace_service.detail(ws.id)
            except Exception:
                continue
            if not detail.run_schedule:
                continue
            if self.run_store.get_active_for_workspace(ws.id):
                logger.info("scheduler skipping workspace %s — run already active", ws.id)
                continue
            if scheduled_now(detail.run_schedule):
                logger.info(
                    "scheduler firing run for workspace %s (schedule=%s)",
                    ws.id,
                    detail.run_schedule,
                )
                self.trigger_service.trigger(ws.id, RunTriggerRequest())
