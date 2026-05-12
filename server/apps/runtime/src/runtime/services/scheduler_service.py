from __future__ import annotations

import logging
import threading
from datetime import datetime

from croniter import croniter

from runtime.models.run import RunTriggerRequest
from runtime.services.run_trigger_service import RunTriggerService
from runtime.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


def scheduled_now(schedule: str, last_fired: datetime | None) -> bool:
    now = datetime.now()
    prev = croniter(schedule, now).get_prev(datetime)
    if last_fired is None:
        return False
    return prev > last_fired


class SchedulerService:
    def __init__(self, workspace_service: WorkspaceService, trigger_service: RunTriggerService) -> None:
        self.workspace_service = workspace_service
        self.trigger_service = trigger_service
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_fired: dict[str, datetime] = {}

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
            self._stop.wait(timeout=60)

    def _tick(self) -> None:
        for ws in self.workspace_service.list():
            try:
                detail = self.workspace_service.detail(ws.id)
            except Exception:
                continue
            if not detail.run_schedule:
                continue
            if scheduled_now(detail.run_schedule, self._last_fired.get(ws.id)):
                logger.info("scheduler firing run for workspace %s (schedule=%s)", ws.id, detail.run_schedule)
                self.trigger_service.trigger(ws.id, RunTriggerRequest())
                self._last_fired[ws.id] = datetime.now()
