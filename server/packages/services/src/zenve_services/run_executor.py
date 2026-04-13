from __future__ import annotations

import json
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


def parse_json_line_by_line(text: str) -> str | list[dict] | dict:
    lines = [line.strip() for line in text.split('\n') if line.strip()]

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


def parse_json_safe(text: str) -> str | list[dict] | dict:
    return parse_json_line_by_line(text)


def write_transcript_json(ctx: RunContext, result: RunResult) -> Path | None:
    """Write run output to {agent_dir}/runs/{YYYY-MM-DD}/{run-id}.json"""
    try:
        runs_dir = Path(ctx.agent_dir) / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        date_dir = runs_dir / datetime.now(UTC).strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{ctx.run_id}.json"
        path = date_dir / filename
        transcript = {
            "run_id": ctx.run_id,
            "agent_slug": ctx.agent_slug,
            "session_id": result.session_id,
            "exit_code": result.exit_code,
            "duration_seconds": result.duration_seconds,
            "stdout": parse_json_safe(result.stdout),
            "stderr": parse_json_safe(result.stderr) if result.stderr else None,
            "outcome": result.outcome,
        }
        path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
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

        if result.session_id:
            run.session_id = result.session_id
            db.commit()

        transcript_path = write_transcript_json(ctx, result)

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
