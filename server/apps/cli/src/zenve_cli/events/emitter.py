from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from zenve_cli.core.config import zenve_dir

logger = logging.getLogger(__name__)

EVENTS_LOG_FILE = "events.log"


class EventEmitter:
    """Emit structured events to a local log + optional HMAC-signed webhook.

    Webhook delivery is fire-and-forget (one attempt in a background thread).
    """

    def __init__(
        self,
        repo_root: Path,
        run_id: str,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> None:
        self._run_id = run_id
        self._webhook_url = webhook_url
        self._webhook_secret = webhook_secret
        self._on_event = on_event
        self._log_path = zenve_dir(repo_root) / EVENTS_LOG_FILE
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def emit(
        self,
        event_type: str,
        agent: str | None = None,
        data: dict | None = None,
    ) -> None:
        event = {
            "run_id": self._run_id,
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": event_type,
            "agent": agent,
            "data": data or {},
        }
        body = json.dumps(event)
        self.write_local(body)
        if self._on_event:
            self._on_event(event)
        if self._webhook_url:
            threading.Thread(target=self.deliver, args=(body,), daemon=True).start()

    def write_local(self, body: str) -> None:
        with self._lock:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(body + "\n")

    def deliver(self, body: str) -> None:
        assert self._webhook_url is not None
        headers = {"Content-Type": "application/json", "X-Zenve-Run-Id": self._run_id}
        if self._webhook_secret:
            sig = hmac.new(
                self._webhook_secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Zenve-Signature"] = f"sha256={sig}"
        try:
            httpx.post(self._webhook_url, content=body, headers=headers, timeout=5.0)
        except Exception:
            try:
                httpx.post(self._webhook_url, content=body, headers=headers, timeout=5.0)
            except Exception as exc:
                logger.warning("Webhook delivery failed: %s", exc)
