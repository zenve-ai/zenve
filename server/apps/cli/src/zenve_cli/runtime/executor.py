from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from zenve_adapters import AdapterRegistry
from zenve_adapters.base import BaseAdapter
from zenve_cli.core.claims import add_claim, expired_claims, load_claims, remove_claim
from zenve_cli.core.discovery import DiscoveredAgent
from zenve_cli.core.pipeline import next_label
from zenve_cli.events import types as et
from zenve_cli.events.emitter import EventEmitter
from zenve_cli.integrations.github.client import GitHubClient, GitHubError
from zenve_cli.integrations.github.labels import (
    CLAIMED_LABEL,
    FAILED_LABEL,
    NEEDS_INPUT_LABEL,
    claim_item,
    transition,
    unclaim_item,
)
from zenve_cli.models.claims import Claim
from zenve_cli.models.run_result import (
    PipelineTransition,
    RunItem,
    RunResultFile,
    TokenUsage,
)
from zenve_cli.models.settings import AgentSettings, ProjectSettings
from zenve_cli.models.snapshot import Snapshot, SnapshotIssue, SnapshotPR
from zenve_cli.runtime.commit import GitError
from zenve_cli.runtime.worktree import commit_and_push_worktree, create_worktree, remove_worktree
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


@dataclass
class DryRunResult:
    agent_name: str
    picks_up: str
    label: str
    item: PlannedItem | None
    context: RunContext


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
    """Return the oldest item that does not carry zenve:claimed."""
    for it in items:
        if CLAIMED_LABEL not in it.labels:
            return it
    return None


def find_snapshot_item(snapshot: Snapshot, item: PlannedItem) -> SnapshotIssue | SnapshotPR | None:
    if item.kind == "issue":
        return next((i for i in snapshot.issues if i.number == item.number), None)
    return next((p for p in snapshot.pull_requests if p.number == item.number), None)


def build_message(run_id: str, agent_name: str, item: PlannedItem | None, snapshot: Snapshot) -> str:
    lines = [f"Run: {run_id}", f"Agent: {agent_name}"]

    if item is None:
        return "\n".join(lines)

    kind_label = "Issue" if item.kind == "issue" else "PR"
    lines.append(f"\n## {kind_label} #{item.number}: {item.title}")

    snap = find_snapshot_item(snapshot, item)
    if snap is None:
        return "\n".join(lines)

    meta: list[str] = []
    if snap.labels:
        meta.append(f"**Labels:** {', '.join(snap.labels)}")
    if snap.assignees:
        meta.append(f"**Assignees:** {', '.join(snap.assignees)}")
    if meta:
        lines.append("\n".join(meta))

    if snap.body:
        lines.append(f"\n### Description\n{snap.body}")

    if snap.comments:
        lines.append(f"\n### Comments ({len(snap.comments)})")
        for c in snap.comments:
            lines.append(f"\n**@{c.author}** · {c.created_at}\n{c.body}")

    return "\n".join(lines)


def build_run_context(
    agent: DiscoveredAgent,
    run_id: str,
    project: ProjectSettings,
    repo_root: Path,
    item: PlannedItem | None,
    snapshot: Snapshot,
    env_vars: dict[str, str],
    project_dir_override: Path | None = None,
) -> RunContext:
    config: dict = dict(agent.settings.adapter_config)
    message = build_message(run_id, agent.name, item, snapshot)
    effective_dir = project_dir_override if project_dir_override is not None else repo_root

    return RunContext(
        agent_dir=str(agent.path),
        project_dir=str(effective_dir.resolve()),
        agent_id=agent.settings.slug,
        agent_slug=agent.settings.slug,
        agent_name=agent.settings.name,
        project_slug=project.project,
        project_description=project.description,
        run_id=run_id,
        adapter_type=agent.settings.adapter_type,
        adapter_config=config,
        message=message,
        heartbeat=agent.settings.heartbeat_interval_seconds > 0,
        tools=agent.settings.tools,
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


def apply_pipeline_transition(
    gh: GitHubClient,
    project: ProjectSettings,
    agent: DiscoveredAgent,
    item: PlannedItem,
    emitter: EventEmitter,
) -> PipelineTransition | None:
    to_label = next_label(project.pipeline, agent.settings.github_label)
    transition(gh, item.number, agent.settings.github_label, to_label)
    emitter.emit(
        et.PIPELINE_END if to_label is None else et.PIPELINE_TRANSITION,
        agent=agent.name,
        data={
            "number": item.number,
            "from": agent.settings.github_label,
            "to": to_label,
        },
    )
    return PipelineTransition(
        from_label=agent.settings.github_label,
        to_label=to_label,
    )


def reconcile_claims(
    gh: GitHubClient,
    snapshot: Snapshot,
    repo_root: Path,
) -> None:
    """Clean up expired and orphaned claims before agents run.

    For each stale claim (expired TTL or present on GitHub but absent from
    claims.json), removes zenve:claimed from GitHub, removes from claims.json,
    and strips the label from the in-memory snapshot so pick_unclaimed sees
    the item as free.
    """
    stale = expired_claims(repo_root)
    stale_numbers = {c.number for c in stale}

    cf = load_claims(repo_root)
    known_numbers = {c.number for c in cf.claims}

    orphan_numbers: set[int] = set()
    for issue in snapshot.issues:
        if CLAIMED_LABEL in issue.labels and issue.number not in known_numbers:
            orphan_numbers.add(issue.number)
    for pr in snapshot.pull_requests:
        if CLAIMED_LABEL in pr.labels and pr.number not in known_numbers:
            orphan_numbers.add(pr.number)

    to_release = stale_numbers | orphan_numbers
    if not to_release:
        return

    for number in to_release:
        unclaim_item(gh, number)
        remove_claim(repo_root, number)
        for issue in snapshot.issues:
            if issue.number == number:
                issue.labels = [lbl for lbl in issue.labels if lbl != CLAIMED_LABEL]
        for pr in snapshot.pull_requests:
            if pr.number == number:
                pr.labels = [lbl for lbl in pr.labels if lbl != CLAIMED_LABEL]


async def run_agent(
    agent: DiscoveredAgent,
    snapshot: Snapshot,
    project: ProjectSettings,
    repo_root: Path,
    run_id: str,
    registry: AdapterRegistry,
    gh: GitHubClient,
    emitter: EventEmitter,
    env_vars: dict[str, str],
    dry_run: bool = False,
) -> DryRunResult | RunResultFile | None:
    """Execute one agent end-to-end — claim → adapter → label transition."""
    items = filter_for_agent(snapshot, agent.settings)
    item: PlannedItem | None = None

    if agent.settings.picks_up != "none" and items:
        item = pick_unclaimed(items)

    if dry_run:
        ctx = build_run_context(agent, run_id, project, repo_root, item, snapshot, env_vars)
        return DryRunResult(
            agent_name=agent.name,
            picks_up=agent.settings.picks_up,
            label=agent.settings.github_label,
            item=item,
            context=ctx,
        )

    emitter.emit(et.AGENT_STARTED, agent=agent.name)

    if agent.settings.mode == "read_only":
        write_tools = {"Write", "Edit", "Bash", "NotebookEdit"}
        flagged = write_tools & set(agent.settings.tools)
        if flagged:
            emitter.emit(
                et.AGENT_MISCONFIGURED,
                agent=agent.name,
                data={"reason": "read_only agent has write-capable tools", "tools": sorted(flagged)},
            )

    if agent.settings.picks_up != "none":
        if not items:
            emitter.emit(et.AGENT_NOTHING_TO_DO, agent=agent.name)
            return None
        if item is None:
            emitter.emit(et.AGENT_NOTHING_TO_DO, agent=agent.name)
            return None

    if item is not None:
        claimed = claim_item(gh, item.number)
        if not claimed:
            emitter.emit(
                et.AGENT_NOTHING_TO_DO,
                agent=agent.name,
                data={"reason": "claim_failed", "number": item.number},
            )
            return None
        add_claim(
            repo_root,
            Claim(
                number=item.number,
                kind=item.kind,
                agent_name=agent.name,
                run_id=run_id,
                claimed_at=now_iso(),
            ),
        )
        emitter.emit(
            et.AGENT_CLAIMED_PR if item.kind == "pull_request" else et.AGENT_CLAIMED_ISSUE,
            agent=agent.name,
            data={"number": item.number, "title": item.title},
        )

    worktree_path: Path | None = None
    worktree_branch: str | None = None

    if agent.settings.mode == "write" and item is not None:
        run_id_short = run_id[:6]
        worktree_path = repo_root / "worktrees" / f"{agent.settings.slug}-{run_id_short}"
        worktree_branch = f"zenve/{agent.settings.slug}/{item.number}-{run_id_short}"
        try:
            create_worktree(repo_root, worktree_path, worktree_branch, project.default_branch)
        except GitError as exc:
            emitter.emit(et.AGENT_FAILED, agent=agent.name, data={"error": str(exc)})
            unclaim_item(gh, item.number)
            remove_claim(repo_root, item.number)
            worktree_path = None
            run_result = RunResultFile(
                run_id=run_id,
                agent=agent.name,
                started_at=now_iso(),
                finished_at=now_iso(),
                duration_seconds=0.0,
                status="failed",
                exit_code=1,
                item=RunItem(type=item.kind, number=item.number, title=item.title),
                error=str(exc),
            )
            write_run_result(agent, run_result)
            return run_result

    started_at = now_iso()
    start_mono = time.monotonic()

    ctx = build_run_context(agent, run_id, project, repo_root, item, snapshot, env_vars, project_dir_override=worktree_path)

    adapter_event_map = {
        "output": et.ADAPTER_OUTPUT,
        "tool_call": et.ADAPTER_TOOL_CALL,
        "tool_result": et.ADAPTER_TOOL_RESULT,
        "usage": et.ADAPTER_USAGE,
        "error": et.ADAPTER_ERROR,
    }
    adapter_errors: list[str] = []

    def on_adapter_event(event_type: str, message: str | None, data: dict | None) -> None:
        mapped = adapter_event_map.get(event_type, f"adapter.{event_type}")
        if mapped == et.ADAPTER_ERROR and message:
            adapter_errors.append(message)
        emitter.emit(mapped, agent=agent.name, data={"message": message, **(data or {})})

    ctx.on_event = on_adapter_event

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
        if item is not None:
            unclaim_item(gh, item.number)
            remove_claim(repo_root, item.number)
            try:
                gh.post_comment(item.number, f"Run failed\n\n{exc!s}")
            except GitHubError:
                pass
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
        if worktree_path is not None:
            try:
                remove_worktree(repo_root, worktree_path)
            except GitError:
                pass
        return run_result

    finished_at = now_iso()

    if result.exit_code == 0:
        run_status = BaseAdapter.parse_run_status(result.outcome or "")
    else:
        run_status = "failed"
    status = run_status if run_status in ("completed", "needs_input") else "failed"
    error_text = result.error
    if status == "failed" and not error_text and adapter_errors:
        error_text = adapter_errors[-1]
    if status == "failed" and not error_text:
        error_text = f"Adapter exited with code {result.exit_code}"

    if (
        agent.settings.mode == "write"
        and worktree_path is not None
        and worktree_branch is not None
        and item is not None
        and status == "completed"
    ):
        try:
            pushed = commit_and_push_worktree(
                worktree_path,
                f"{project.commit_message_prefix} {run_id} — {agent.settings.slug}: #{item.number}",
                worktree_branch,
            )
            if pushed:
                pr_body = f"Closes #{item.number}" if item.kind == "issue" else f"See #{item.number}"
                gh.create_pr(
                    title=item.title,
                    body=pr_body,
                    head=worktree_branch,
                    base=project.default_branch,
                )
        except (GitError, GitHubError):
            status = "failed"

    pipeline_transition: PipelineTransition | None = None
    if item is not None:
        if status == "completed":
            pipeline_transition = apply_pipeline_transition(gh, project, agent, item, emitter)
        elif status == "needs_input":
            unclaim_item(gh, item.number)
            try:
                gh.add_labels(item.number, [NEEDS_INPUT_LABEL])
            except GitHubError:
                pass
        else:
            unclaim_item(gh, item.number)
            try:
                gh.add_labels(item.number, [FAILED_LABEL])
            except GitHubError:
                pass
        if status == "completed":
            comment_body = f"Run complete\n\n{result.outcome}" if result.outcome else "Run complete"
        elif status == "needs_input":
            comment_body = f"Run needs input\n\n{result.outcome}" if result.outcome else "Run needs input"
        else:
            comment_body = f"Run failed\n\n{error_text}" if error_text else "Run failed"
        try:
            gh.post_comment(item.number, comment_body)
        except GitHubError:
            pass
        remove_claim(repo_root, item.number)

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
        error=error_text,
    )
    write_run_result(agent, run_result)

    if status == "completed":
        event_type = et.AGENT_COMPLETED
    elif status == "needs_input":
        event_type = et.AGENT_NEEDS_INPUT
    else:
        event_type = et.AGENT_FAILED
    emitter.emit(
        event_type,
        agent=agent.name,
        data={
            "exit_code": result.exit_code,
            "duration_seconds": result.duration_seconds,
            **({"error": error_text} if status == "failed" and error_text else {}),
        },
    )
    if worktree_path is not None:
        try:
            remove_worktree(repo_root, worktree_path)
        except GitError:
            pass
    return run_result
