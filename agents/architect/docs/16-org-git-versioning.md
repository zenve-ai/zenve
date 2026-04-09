# Chunk 16 — Org-Level Git Versioning

## Goal
Give each organization a single git repository at its filesystem root. The gateway commits once per agent run — after the adapter returns — using a thin `OrgRepo` helper. Agents never interact with git directly.

## Depends On
- Chunk 07 (Celery Run Execution — commit step is added to `execute_agent_run`)
- Chunk 08 (Runs CRUD — `pre_commit_sha` / `post_commit_sha` fields on the Run model)

## Referenced By
- Chunk 10 — Heartbeat Scheduler (heartbeat runs are committed by the same lifecycle)
- Chunk 12 — Collaboration Execution Engine (collaboration sub-runs go through the same commit step)

## Filesystem Layout

```
/data/orgs/{org_slug}/
  .git/                 ← one repo per org
  .gitignore            ← ignores agents/*/runs/
  project/              ← shared org-level state (specs, docs, context)
  agents/
    {agent_slug}/
      SOUL.md
      AGENTS.md
      memory/
      workspace/
      runs/             ← gitignored (transcripts)
```

## Deliverables

### 1. Dependencies

Add to project:
- `GitPython`

### 2. OrgRepo Helper — `services/org_repo.py`

Wraps all git operations. The Celery task calls this; no raw git calls inline in tasks.

```python
class OrgRepo:
    def __init__(self, org: Organization): ...

    def init_if_needed(self) -> None:
        """Initialize git repo and .gitignore if org dir has no .git."""

    def head_sha(self) -> str | None:
        """Return current HEAD sha, or None if repo has no commits."""

    def commit_run(
        self,
        agent_slug: str,
        run_id: str,
        trigger: str,
        summary: str,
    ) -> str:
        """
        Acquire per-org lock, stage all changes, commit, release lock.
        Returns the new HEAD sha.
        """

    def rollback_agent(
        self,
        agent_slug: str,
        pre_sha: str,
        run_id: str,
    ) -> None:
        """
        Restore agents/{agent_slug}/ to pre_sha and commit the rollback.
        Does NOT touch project/.
        """
```

### 3. Commit Convention

**Author:** `{agent_slug} <{agent_slug}@{org_slug}.zenve.ai>`

**Message:**
```
run {run_id} ({trigger}): {short summary}

Run: {run_id}
Agent: {agent_slug}
Trigger: {heartbeat|manual|collaboration}
```

This enables three filter styles out of the box:
```bash
git log -- agents/devy/        # by path
git log --author=devy          # by author
git log --grep="Run: abc123"   # by run id
```

### 4. Commit Lifecycle in `execute_agent_run`

```
1. pre_sha  = org_repo.head_sha()
2. adapter.execute(ctx)             ← agent writes files freely
3. org_repo.commit_run(...)         ← acquire lock, git add -A, commit, release
4. post_sha = new HEAD
5. run_service.update(pre_commit_sha=pre_sha, post_commit_sha=post_sha)
```

On adapter exception:
```
org_repo.rollback_agent(agent_slug, pre_sha, run_id)
run_service.update(pre_commit_sha=pre_sha, status="failed")
```

### 5. Concurrency Lock

Git takes a per-repo index lock; concurrent commits within the same org must serialize.

- **Production:** Redis distributed lock (`{org_slug}:git_lock`, TTL 30s).
- **Dev / test:** Per-process `asyncio.Lock` keyed by org slug, stored in a module-level dict.

The lock wraps only the commit step, not adapter execution. Adapters run fully in parallel; commits serialize for a few hundred milliseconds each.

### 6. Data Model Additions — `db/models.py`

Add columns to `organizations`:

```
git_remote_url      VARCHAR NULL
git_remote_name     VARCHAR DEFAULT 'origin'
git_push_policy     VARCHAR DEFAULT 'on_schedule'  -- manual | on_commit | on_schedule
last_pushed_at      TIMESTAMP NULL
last_pushed_sha     VARCHAR NULL
```

Add columns to `runs`:

```
pre_commit_sha      VARCHAR(40) NULL
post_commit_sha     VARCHAR(40) NULL
```

### 7. Remote Push

Default policy is `on_schedule` with a 5-minute APScheduler job. Users can also trigger a manual push:

```
POST /api/v1/orgs/{id}/git/push    → trigger immediate push to configured remote
GET  /api/v1/orgs/{id}/git/status  → last_pushed_at, last_pushed_sha, push errors
```

Transient push failures are retried (up to 3×). Persistent failures surface on the status endpoint. Remote credentials live in the secrets store, not the DB.

### 8. Diff Endpoint — `api/routes/run.py`

```
GET /api/v1/runs/{run_id}/diff
  → git diff <pre_sha>..<post_sha> -- agents/{agent_slug}/

GET /api/v1/runs/{run_id}/diff?include_shared=true
  → git diff <pre_sha>..<post_sha> -- agents/{agent_slug}/ project/
```

Path scoping keeps the diff focused on what this specific run changed, even when other runs committed in between.

Returns 404 if `pre_commit_sha` or `post_commit_sha` is null (run did not complete a commit).

### 9. .gitignore Template

The `.gitignore` written at `init_if_needed()` time:

```
agents/*/runs/
*.pyc
__pycache__/
```

## Notes

- `OrgRepo.init_if_needed()` is called by `FilesystemService.create_org_dir()` (Chunk 03) so every org starts with a git repo.
- GitPython's `Repo` object should be instantiated once per task invocation, not cached across tasks.
- `head_sha()` returns `None` on a freshly initialized repo (no commits yet); the task must handle this case and skip the rollback if `pre_sha` is `None`.
- `.git` size growth is handled by periodic `git gc`; not a near-term concern.
- Hard-deleting an agent's history (e.g. with `git filter-repo`) is not exposed through the API. Soft delete is the default.
