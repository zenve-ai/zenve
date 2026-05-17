"""
zenve-issues basic usage.

SQLite runs automatically (no auth needed).
GitHub requires GITHUB_REPO env var; token is auto-resolved from
ZENVE_GH_TOKEN env var or `gh auth token`.

Usage (from server/):
    uv run python examples/zenve_issues_usage.py
"""
import os

from zenve_issues import (
    GitHubIssueAdapter,
    GitHubIssueConfig,
    IssueAdapterRegistry,
    IssueCreate,
    IssueListFilter,
    IssueUpdate,
    SQLiteIssueAdapter,
    SQLiteIssueConfig,
)

registry = IssueAdapterRegistry()
registry.register(SQLiteIssueAdapter())
registry.register(GitHubIssueAdapter())

# --- SQLite: full CRUD against an in-memory database ---
print("=== SQLite ===")
adapter = registry.get("sqlite")
cfg = SQLiteIssueConfig(db_path=":memory:")

issue = adapter.create(cfg, IssueCreate(title="My first issue", body="Hello from zenve-issues"))
print(f"Created:  #{issue.id} — {issue.title}")

issues = adapter.list(cfg, IssueListFilter(state="open"))
print(f"Listed:   {len(issues)} open issue(s)")

fetched = adapter.get(cfg, issue.id)
print(f"Fetched:  #{fetched.id} state={fetched.state}")

updated = adapter.update(cfg, issue.id, IssueUpdate(title="Updated title"))
print(f"Updated:  #{updated.id} — {updated.title}")

adapter.delete(cfg, issue.id)
print("Deleted.  SQLite CRUD complete.")

# --- GitHub: same interface, different backend ---
print("\n=== GitHub ===")
repo = os.getenv("GITHUB_REPO", "")

if not repo:
    print("Skipped (set GITHUB_REPO to enable; token auto-resolved from ZENVE_GH_TOKEN or gh CLI).")
else:
    gh = registry.get("github")
    cfg = GitHubIssueConfig(repo=repo)  # token resolved automatically

    if not gh.health_check(cfg):
        print("GitHub health check failed — check token and repo.")
    else:
        new = gh.create(cfg, IssueCreate(title="[zenve-issues example]", body="Created by zenve_issues_usage.py"))
        print(f"Created:  #{new.id} — {new.title}")

        issues = gh.list(cfg, IssueListFilter(state="open", limit=5))
        print(f"Listed:   {len(issues)} open issue(s) (limit=5)")

        fetched = gh.get(cfg, new.id)
        print(f"Fetched:  #{fetched.id} state={fetched.state}")

        updated = gh.update(cfg, new.id, IssueUpdate(title="[zenve-issues example] updated"))
        print(f"Updated:  #{updated.id} — {updated.title}")

        gh.delete(cfg, new.id)  # closes the issue (GitHub has no delete endpoint)
        print("Deleted:  issue closed (delete = close on GitHub). GitHub CRUD complete.")
