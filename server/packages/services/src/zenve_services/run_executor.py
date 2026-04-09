from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from zenve_adapters.registry import AdapterRegistry
from zenve_db.database import Session
from zenve_db.models import Run
from zenve_models.adapter import RunContext, RunResult

logger = logging.getLogger(__name__)


def write_transcript(ctx: RunContext, result: RunResult) -> Path | None:
    """Write run output to {agent_dir}/runs/{timestamp}_{run_id[:8]}.md"""
    try:
        runs_dir = Path(ctx.agent_dir) / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        filename = f"{ts}_{ctx.run_id[:8]}.md"
        path = runs_dir / filename
        lines = [
            f"# Run {ctx.run_id}",
            f"- agent: {ctx.agent_slug}",
            f"- exit_code: {result.exit_code}",
            f"- duration: {result.duration_seconds:.2f}s",
            "",
            "## stdout",
            "```",
            result.stdout,
            "```",
        ]
        if result.stderr:
            lines += ["", "## stderr", "```", result.stderr, "```"]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
    except Exception:
        logger.exception("Failed to write transcript for run %s", ctx.run_id)
        return None


async def execute_run(
    run_id: str,
    ctx: RunContext,
    adapter_registry: AdapterRegistry,
) -> None:
    """Background async task: execute one agent run and persist results.

    Uses a fresh DB session (not FastAPI's Depends) since this runs outside
    the request lifecycle.
    """
    db = Session()
    try:
        run: Run | None = db.get(Run, run_id)
        if not run or run.status != "queued":
            return

        run.status = "running"
        run.started_at = datetime.now(UTC)
        db.commit()

        adapter = adapter_registry.get(ctx.adapter_type)
        result: RunResult = await adapter.execute(ctx)

        transcript_path = write_transcript(ctx, result)

        # Re-fetch in case cancelled while running
        db.refresh(run)
        if run.status != "cancelled":
            run.status = "completed" if result.exit_code == 0 else "failed"
            run.exit_code = result.exit_code
            run.token_usage = result.token_usage
            run.transcript_path = str(transcript_path) if transcript_path else None
            run.error_summary = result.error
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
