from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path

from zenve_adapters import AdapterRegistry
from zenve_core.context import build_run_context
from zenve_core.result import AgentRunResult
from zenve_core.worktree import cleanup_worktree, setup_worktree
from zenve_engine.discovery import DiscoveredAgent
from zenve_engine.events import types as et
from zenve_engine.events.emitter import EventEmitter
from zenve_engine.exec.executor import determine_run_status
from zenve_engine.models.run_result import TokenUsage
from zenve_engine.models.settings import WorkspaceSettings

_ADAPTER_EVENT_MAP = {
    "output": et.ADAPTER_OUTPUT,
    "tool_call": et.ADAPTER_TOOL_CALL,
    "tool_result": et.ADAPTER_TOOL_RESULT,
    "usage": et.ADAPTER_USAGE,
    "error": et.ADAPTER_ERROR,
}


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def execute(
    agent: DiscoveredAgent,
    workspace: WorkspaceSettings,
    workspace_dir: Path,
    run_id: str,
    message: str,
    env_vars: dict[str, str],
    registry: AdapterRegistry,
    emitter: EventEmitter,
    workspace_id: str = "",
    cancel_event: asyncio.Event | None = None,
) -> AgentRunResult:
    emitter.emit(et.AGENT_STARTED, agent=agent.name)

    worktree_path, worktree_branch = setup_worktree(workspace_dir, agent.settings.slug, run_id, workspace)

    ctx = build_run_context(
        agent=agent,
        run_id=run_id,
        workspace=workspace,
        workspace_dir=workspace_dir,
        message=message,
        env_vars=env_vars,
        workspace_id=workspace_id,
        workspace_dir_override=worktree_path,
    )

    adapter_errors: list[str] = []

    def on_adapter_event(event_type: str, msg: str | None, data: dict | None) -> None:
        mapped = _ADAPTER_EVENT_MAP.get(event_type, f"adapter.{event_type}")
        if mapped == et.ADAPTER_ERROR and msg:
            adapter_errors.append(msg)
        emitter.emit(mapped, agent=agent.name, data={"message": msg, **(data or {})})

    ctx.on_event = on_adapter_event

    started_at = now_iso()
    start_mono = time.monotonic()

    try:
        adapter = registry.get(ctx.adapter_type)
        result = await adapter.execute(ctx, cancel_event=cancel_event)
    except Exception as exc:
        duration = time.monotonic() - start_mono
        emitter.emit(et.AGENT_FAILED, agent=agent.name, data={"error": str(exc)})
        cleanup_worktree(workspace_dir, worktree_path, worktree_branch)
        return AgentRunResult(
            run_id=run_id,
            agent_slug=agent.settings.slug,
            agent_name=agent.settings.name,
            started_at=started_at,
            finished_at=now_iso(),
            duration_seconds=duration,
            status="failed",
            exit_code=1,
            error=str(exc),
        )

    finished_at = now_iso()
    duration = time.monotonic() - start_mono

    cleanup_worktree(workspace_dir, worktree_path, worktree_branch)

    status, error_text = determine_run_status(result, adapter_errors)

    token_usage: TokenUsage | None = None
    if result.token_usage:
        token_usage = TokenUsage(
            input_tokens=result.token_usage.get("input_tokens", 0),
            output_tokens=result.token_usage.get("output_tokens", 0),
            cost_usd=result.token_usage.get("cost_usd"),
        )

    terminal_event = {
        "completed": et.AGENT_COMPLETED,
        "needs_input": et.AGENT_NEEDS_INPUT,
        "changes_requested": et.AGENT_CHANGES_REQUESTED,
    }.get(status, et.AGENT_FAILED)

    event_data: dict = {"exit_code": result.exit_code, "duration_seconds": duration}
    if status == "failed" and error_text:
        event_data["error"] = error_text
    emitter.emit(terminal_event, agent=agent.name, data=event_data)

    return AgentRunResult(
        run_id=run_id,
        agent_slug=agent.settings.slug,
        agent_name=agent.settings.name,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
        status=status,
        exit_code=result.exit_code,
        output=result.outcome,
        error=error_text,
        token_usage=token_usage,
    )
