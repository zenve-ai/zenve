"""Public engine API.

`run(workspace_dir)` orchestrates a single live run end-to-end:
load env/config → discover agents → snapshot GitHub → reconcile claims →
run all agents in parallel → commit `.zenve/agents/` → emit RUN_COMPLETED.

`snapshot(workspace_dir)` writes `.zenve/snapshot.json` and returns the
in-memory Snapshot. No agents run.

Both functions are forward-facing: today they back the CLI commands; later
the runtime daemon (`apps/runtime`) will call `run()` directly.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from zenve_adapters import AdapterRegistry, build_default_registry
from zenve_engine.config import load_workspace_settings
from zenve_engine.discovery import DiscoveredAgent, discover_agents
from zenve_engine.errors import DirtyTreeError, MissingRemoteBranchError
from zenve_engine.events import types as et
from zenve_engine.events.emitter import EventEmitter
from zenve_engine.exec.executor import reconcile_claims
from zenve_engine.exec.parallel import run_all
from zenve_engine.git.commit import (
    GitError,
    commit_staged,
    commit_zenve_dir,
    fetch_origin,
    has_dirty_outside_zenve,
    has_dirty_zenve,
    remote_branch_exists,
    run_git,
    stage_zenve,
)
from zenve_engine.github.client import GitHubClient
from zenve_engine.github.snapshot import build_snapshot, write_snapshot
from zenve_engine.models.run_result import RunResultFile
from zenve_engine.models.snapshot import Snapshot
from zenve_issues import BaseIssueAdapter, build_issues_adapter


@dataclass
class RunReport:
    run_id: str
    agents: list[DiscoveredAgent]
    results: list[RunResultFile] = field(default_factory=list)
    committed: bool = False
    summary: str = ""


def snapshot(
    workspace_dir: Path,
    *,
    run_id: str,
    github_token: str,
    repo: str,
    issues_adapter: BaseIssueAdapter | None = None,
    issues_adapter_type: str = "github",
) -> Snapshot:
    """Fetch issues snapshot and write it to `.zenve/snapshot.json`."""
    workspace = load_workspace_settings(workspace_dir)
    effective_type = workspace.issues.adapter or issues_adapter_type
    adapter = issues_adapter or build_issues_adapter(effective_type, workspace_dir, github_token, repo)
    with GitHubClient(github_token, repo) as gh:
        snap = build_snapshot(adapter, gh, run_id)
    write_snapshot(workspace_dir, snap)
    return snap


def run(
    workspace_dir: Path,
    *,
    run_id: str,
    github_token: str,
    repo: str,
    webhook_url: str | None = None,
    webhook_secret: str | None = None,
    only_agent: str | None = None,
    env_vars: dict[str, str] | None = None,
    on_event: Callable[[dict], None] | None = None,
    registry: AdapterRegistry | None = None,
    auto_commit_zenve: bool = False,
    issues_adapter: BaseIssueAdapter | None = None,
    issues_adapter_type: str = "github",
) -> RunReport:
    """Execute a full live run against `workspace_dir`.

    Preflight (raises before touching anything):
    - Working tree must be clean outside `.zenve/`. Otherwise `DirtyTreeError`.
      Reason: a successful `artifact_pr` merge runs `git reset --hard origin/<branch>`
      in the parent repo, which silently destroys uncommitted work.
    - `.zenve/` must be clean too, otherwise `commit_agents` at the end would bundle
      unrelated edits into the auto-commit. Pass `auto_commit_zenve=True` to commit
      and push `.zenve/` first instead of failing.
    - `origin/<default_branch>` must exist after `git fetch origin`. Otherwise
      `MissingRemoteBranchError`.

    Then: discover → emitter → snapshot → reconcile_claims → run_all → commit_agents.
    """
    workspace = load_workspace_settings(workspace_dir)

    if has_dirty_outside_zenve(workspace_dir):
        raise DirtyTreeError(
            f"{workspace_dir} has uncommitted changes outside .zenve/. "
            "Commit, stash, or discard them — a successful artifact_pr run would "
            "git reset --hard the parent and wipe them."
        )

    if has_dirty_zenve(workspace_dir):
        if not auto_commit_zenve:
            raise DirtyTreeError(
                f"{workspace_dir}/.zenve/ has uncommitted changes. Commit them first "
                "or pass auto_commit_zenve=True to let the engine commit and push them."
            )
        commit_zenve_dir(
            workspace_dir,
            f"{workspace.commit_message_prefix} update .zenve config",
            branch=workspace.default_branch,
        )

    fetch_origin(workspace_dir)
    if not remote_branch_exists(workspace_dir, workspace.default_branch):
        raise MissingRemoteBranchError(
            f"origin/{workspace.default_branch} not found after fetch in {workspace_dir}"
        )

    agents = discover_agents(workspace_dir, only=only_agent)

    emitter = EventEmitter(
        repo_root=workspace_dir,
        run_id=run_id,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        on_event=on_event,
    )

    if not agents:
        emitter.emit(et.RUN_STARTED, data={"agents": [], "repo": repo, "dry_run": False})
        try:
            stage_zenve(workspace_dir)
            emitter.emit(et.RUN_COMPLETED, data={"committed": False, "summary": "", "agents": 0})
            run_git(["add", str(emitter.log_path)], workspace_dir)
            commit_staged(workspace_dir, f"{workspace.commit_message_prefix} {run_id}", branch=workspace.default_branch)
        except GitError as exc:
            emitter.emit(et.RUN_FAILED, data={"error": str(exc)})
        return RunReport(run_id=run_id, agents=[])

    emitter.emit(
        et.RUN_STARTED,
        data={"agents": [a.name for a in agents], "repo": repo, "dry_run": False},
    )

    base_env = {"ZENVE_RUN_ID": run_id, "GH_TOKEN": github_token}
    if env_vars:
        base_env = {**env_vars, **base_env}

    reg = registry or build_default_registry()
    effective_type = workspace.issues.adapter or issues_adapter_type
    adapter = issues_adapter or build_issues_adapter(effective_type, workspace_dir, github_token, repo)

    with GitHubClient(github_token, repo) as gh:
        snap = build_snapshot(adapter, gh, run_id)
        write_snapshot(workspace_dir, snap)
        emitter.emit(
            et.SNAPSHOT_FETCHED,
            data={
                "issues": len(snap.issues),
                "pull_requests": len(snap.pull_requests),
                "branches": len(snap.branches),
            },
        )

        reconcile_claims(adapter, snap, workspace_dir)

        results = asyncio.run(
            run_all(
                agents=agents,
                snapshot=snap,
                workspace=workspace,
                repo_root=workspace_dir,
                run_id=run_id,
                registry=reg,
                issues_adapter=adapter,
                gh=gh,
                emitter=emitter,
                env_vars=base_env,
                dry_run=False,
            )
        )

    summaries = [r for r in results if isinstance(r, RunResultFile)]
    summary = ", ".join(
        f"{r.agent}: {r.status}{' #' + str(r.item.number) if r.item else ''}"
        for r in summaries
    )

    emitter.emit(et.RUN_COMMITTING)

    # Stage the full .zenve/ dir first so the transcript is included in the commit.
    # Then emit RUN_COMPLETED (which writes the final event to the transcript file),
    # re-stage the transcript to capture that event, and only then commit+push.
    committed = False
    try:
        stage_zenve(workspace_dir)

        emitter.emit(
            et.RUN_COMPLETED,
            data={"committed": False, "summary": summary, "agents": len(summaries)},
        )

        run_git(["add", str(emitter.log_path)], workspace_dir)

        title = f"{workspace.commit_message_prefix} {run_id}"
        if summary:
            title = f"{title} — {summary}"
        committed = commit_staged(workspace_dir, title, branch=workspace.default_branch)
    except GitError as exc:
        emitter.emit(et.RUN_FAILED, data={"error": str(exc)})

    return RunReport(
        run_id=run_id,
        agents=agents,
        results=summaries,
        committed=committed,
        summary=summary,
    )
