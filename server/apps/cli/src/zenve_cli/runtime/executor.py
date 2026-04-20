from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from zenve_adapters import AdapterRegistry
from zenve_cli.core.discovery import DiscoveredAgent
from zenve_cli.core.pipeline import next_label
from zenve_cli.events import types as et
from zenve_cli.events.emitter import EventEmitter
from zenve_cli.github.client import GitHubClient
from zenve_cli.github.labels import claim_item, transition
from zenve_cli.models.run_result import (
    PipelineTransition,
    RunItem,
    RunResultFile,
    TokenUsage,
)
from zenve_cli.models.settings import AgentSettings, ProjectSettings
from zenve_cli.models.snapshot import Snapshot
from zenve_models.adapter import RunContext

logger = logging.getLogger(__name__)

ItemKind = Literal["issue", "pull_request"]


@dataclass
class PlannedItem:
    kind: ItemKind
    number: int
    title: str
    labels: list[str]
    assignees: list[str]
    created_at: str


def filter_for_agent(snapshot: Snapshot, settings: AgentSettings) -> list[PlannedItem]:
    """Return snapshot items that match this agent's label and picks_up filter."""
    if settings.picks_up == "none":
        return []

    wants_issues = settings.picks_up in ("issues", "both")
    wants_prs = settings.picks_up in ("pull_requests", "both")

    items: list[PlannedItem] = []
    if wants_issues:
        items.extend(
            PlannedItem(
                kind="issue",
                number=i.number,
                title=i.title,
                labels=i.labels,
                assignees=i.assignees,
                created_at=i.created_at,
            )
            for i in snapshot.issues
            if settings.github_label in i.labels
        )
    if wants_prs:
        items.extend(
            PlannedItem(
                kind="pull_request",
                number=p.number,
                title=p.title,
                labels=p.labels,
                assignees=p.assignees,
                created_at=p.created_at,
            )
            for p in snapshot.pull_requests
            if settings.github_label in p.labels
        )
    items.sort(key=lambda it: (it.created_at, it.number))
    return items


def pick_unclaimed(items: list[PlannedItem]) -> PlannedItem | None:
    """Return the oldest item that is not already assigned."""
    for it in items:
        if not it.assignees:
            return it
    return None


def build_run_context(
    agent: DiscoveredAgent,
    run_id: str,
    project: ProjectSettings,
    item: PlannedItem | None,
    env_vars: dict[str, str],
) -> RunContext:
    config: dict = {}
    if agent.settings.model:
        config["model"] = agent.settings.model

    message_lines = [f"Run: {run_id}", f"Agent: {agent.name}"]
    if item is not None:
        message_lines.append(f"{item.kind} #{item.number}: {item.title}")
    message = "\n".join(message_lines)

    return RunContext(
        agent_dir=str(agent.path),
        agent_id=agent.name,
        agent_slug=agent.name,
        agent_name=agent.settings.display_name or agent.name,
        org_id=project.project,
        org_slug=project.project,
        run_id=run_id,
        adapter_type=agent.settings.adapter_type,
        adapter_config=config,
        message=message,
        heartbeat=False,
        gateway_url="",
        agent_token="",
        env_vars=env_vars,
    )


def write_run_result(agent: DiscoveredAgent, result: RunResultFile) -> Path:
    runs_dir = agent.path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{result.run_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def run_agent(
    agent: DiscoveredAgent,
    snapshot: Snapshot,
    project: ProjectSettings,
    run_id: str,
    registry: AdapterRegistry,
    gh: GitHubClient,
    bot_login: str,
    emitter: EventEmitter,
    env_vars: dict[str, str],
    dry_run: bool = False,
) -> RunResultFile | None:
    """Execute one agent end-to-end — claim → adapter → label transition."""
    emitter.emit(et.AGENT_STARTED, agent=agent.name)

    items = filter_for_agent(snapshot, agent.settings)
    item: PlannedItem | None = None

    if agent.settings.picks_up != "none":
        if not items:
            emitter.emit(et.AGENT_NOTHING_TO_DO, agent=agent.name)
            return None
        item = pick_unclaimed(items)
        if item is None:
            emitter.emit(et.AGENT_NOTHING_TO_DO, agent=agent.name)
            return None

    if dry_run:
        data: dict = {"picks_up": agent.settings.picks_up, "label": agent.settings.github_label}
        if item is not None:
            data["item"] = {"kind": item.kind, "number": item.number, "title": item.title}
        emitter.emit("agent.dry_run", agent=agent.name, data=data)
        return None

    if item is not None:
        claimed = claim_item(gh, item.number, bot_login)
        if not claimed:
            emitter.emit(
                et.AGENT_NOTHING_TO_DO,
                agent=agent.name,
                data={"reason": "claim_failed", "number": item.number},
            )
            return None
        emitter.emit(
            et.AGENT_CLAIMED_PR if item.kind == "pull_request" else et.AGENT_CLAIMED_ISSUE,
            agent=agent.name,
            data={"number": item.number, "title": item.title},
        )

    started_at = now_iso()
    start_mono = time.monotonic()

    ctx = build_run_context(agent, run_id, project, item, env_vars)

    try:
        adapter = registry.get(ctx.adapter_type)
        result = await adapter.execute(ctx)
    except Exception as exc:
        duration = time.monotonic() - start_mono
        emitter.emit(
            et.AGENT_FAILED,
            agent=agent.name,
            data={"error": str(exc)},
        )
        run_result = RunResultFile(
            run_id=run_id,
            agent=agent.name,
            started_at=started_at,
            finished_at=now_iso(),
            duration_seconds=duration,
            status="failed",
            exit_code=1,
            item=RunItem(type=item.kind, number=item.number, title=item.title)
            if item is not None
            else None,
            error=str(exc),
        )
        write_run_result(agent, run_result)
        return run_result

    finished_at = now_iso()

    pipeline_transition: PipelineTransition | None = None
    if item is not None:
        to_label = next_label(project.pipeline, agent.settings.github_label)
        transition(gh, item.number, agent.settings.github_label, to_label)
        pipeline_transition = PipelineTransition(
            from_label=agent.settings.github_label,
            to_label=to_label,
        )
        emitter.emit(
            et.PIPELINE_END if to_label is None else et.PIPELINE_TRANSITION,
            agent=agent.name,
            data={
                "number": item.number,
                "from": agent.settings.github_label,
                "to": to_label,
            },
        )

    status = "completed" if result.exit_code == 0 else "failed"
    token_usage = (
        TokenUsage(
            input_tokens=result.token_usage.get("input_tokens", 0),
            output_tokens=result.token_usage.get("output_tokens", 0),
            cost_usd=result.token_usage.get("cost_usd"),
        )
        if result.token_usage
        else None
    )

    run_result = RunResultFile(
        run_id=run_id,
        agent=agent.name,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=result.duration_seconds,
        status=status,
        exit_code=result.exit_code,
        item=RunItem(type=item.kind, number=item.number, title=item.title)
        if item is not None
        else None,
        pipeline_transition=pipeline_transition,
        token_usage=token_usage,
        error=result.error,
    )
    write_run_result(agent, run_result)

    emitter.emit(
        et.AGENT_COMPLETED if status == "completed" else et.AGENT_FAILED,
        agent=agent.name,
        data={"exit_code": result.exit_code, "duration_seconds": result.duration_seconds},
    )
    return run_result
