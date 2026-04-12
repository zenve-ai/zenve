from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from zenve_adapters.registry import AdapterRegistry
from zenve_config.settings import get_settings
from zenve_db.database import Session
from zenve_db.models import Agent, Run
from zenve_models.adapter import RunContext, RunResult
from zenve_services.run_event import RunEventService

logger = logging.getLogger(__name__)


class RunExecutor:
    def __init__(self, adapter_registry: AdapterRegistry):
        self.adapter_registry = adapter_registry

    def build_context(
        self,
        agent: Agent,
        run_id: str,
        message: str | None = None,
        heartbeat: bool = False,
        agent_token: str = "",
        extra_env: dict | None = None,
        adapter_type: str | None = None,
        adapter_config: dict | None = None,
    ) -> RunContext:
        """Build a RunContext from an Agent ORM record.

        agent.organization must be loaded before calling this.
        adapter_type and adapter_config override the agent's defaults when provided.
        """
        resolved_adapter_type = adapter_type or agent.adapter_type
        resolved_adapter_config = {**(agent.adapter_config or {}), **(adapter_config or {})}
        return RunContext(
            agent_dir=agent.dir_path,
            agent_id=agent.id,
            agent_slug=agent.slug,
            agent_name=agent.name,
            org_id=agent.org_id,
            org_slug=agent.organization.slug,
            run_id=run_id,
            adapter_type=resolved_adapter_type,
            adapter_config=resolved_adapter_config,
            message=message,
            heartbeat=heartbeat,
            gateway_url=get_settings().gateway_url,
            agent_token=agent_token,
            env_vars=extra_env or {},
        )

    async def execute(self, run_id: str, ctx: RunContext) -> None:
        """Background async task: execute one agent run and persist results.

        Opens its own DB session — runs outside the request lifecycle.
        """
        def on_event(event_type: str, content: str | None = None, metadata: dict | None = None) -> None:
            ev_db = Session()
            try:
                RunEventService(ev_db).create(run_id=run_id, event_type=event_type, content=content, meta=metadata)
                logger.info("[RUN] (%s, %s, %s)", event_type, content, metadata)
            except Exception:
                logger.exception("Failed to persist run event for run %s", run_id)
            finally:
                ev_db.close()

        ctx.on_event = on_event

        db = Session()
        try:
            run: Run | None = db.get(Run, run_id)
            if not run or run.status != "queued":
                return

            run.status = "running"
            run.started_at = datetime.now(UTC)
            db.commit()

            logger.info(f"Run started: {run_id}")

            adapter = self.adapter_registry.get(ctx.adapter_type)
            result: RunResult = await adapter.execute(ctx)

            logger.info(f"Writing transcript for run: {run_id}")
            transcript_path = self.write_transcript_json(ctx, result)

            # Re-fetch in case cancelled while running
            db.refresh(run)
            if run.status != "cancelled":
                if result.outcome:
                    run.status = adapter.parse_run_status(result.outcome)
                else:
                    run.status = "completed" if result.exit_code == 0 else "failed"
                run.exit_code = result.exit_code
                run.token_usage = result.token_usage
                run.transcript_path = str(transcript_path) if transcript_path else None
                run.error_summary = result.error
                run.outcome = result.outcome
            run.finished_at = datetime.now(UTC)
            db.commit()

        except Exception as exc:
            logger.exception("Run %s raised an unexpected error", run_id)
            try:
                db.rollback()
                run = db.get(Run, run_id)
                if run and run.status not in ("cancelled", "completed", "failed"):
                    run.status = "failed"
                    run.finished_at = datetime.now(UTC)
                    run.error_summary = str(exc)
                    db.commit()
            except Exception:
                logger.exception("Failed to mark run %s as failed after error", run_id)
        finally:
            db.close()

    def write_transcript_json(self, ctx: RunContext, result: RunResult) -> Path | None:
        """Write run output to {agent_dir}/runs/{YYYY-MM-DD}/{run-id}.json"""
        try:
            runs_dir = Path(ctx.agent_dir) / "runs"
            date_dir = runs_dir / datetime.now(UTC).strftime("%Y-%m-%d")
            date_dir.mkdir(parents=True, exist_ok=True)

            path = date_dir / f"{ctx.run_id}.json"
            transcript = {
                "run_id": ctx.run_id,
                "agent_slug": ctx.agent_slug,
                "adapter_type": ctx.adapter_type,
                "adapter_config": ctx.adapter_config,
                "exit_code": result.exit_code,
                "duration_seconds": result.duration_seconds,
                "stdout": self.parse_json_safe(result.stdout),
                "stderr": self.parse_json_safe(result.stderr) if result.stderr else None,
                "outcome": result.outcome,
            }
            path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
            return path
        except Exception:
            logger.exception("Failed to write transcript for run %s", ctx.run_id)
            return None

    def parse_json_safe(self, text: str) -> str | list[dict] | dict:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) > 1:
            try:
                return [json.loads(line) for line in lines]
            except json.JSONDecodeError:
                pass
        try:
            parsed = json.loads(text)
            if isinstance(parsed, (dict, list)):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return text
