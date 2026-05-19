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
registry.add(SQLiteIssueAdapter(SQLiteIssueConfig(db_path=":memory:")))

# --- SQLite: full CRUD against an in-memory database ---
print("=== SQLite ===")
adapter = registry.get("sqlite")

issue = adapter.create(IssueCreate(title="My first issue", body="Hello from zenve-issues"))
print(f"Created:  #{issue.id} — {issue.title}")

issues = adapter.list(IssueListFilter(state="open"))
print(f"Listed:   {len(issues)} open issue(s)")

fetched = adapter.get(issue.id)
print(f"Fetched:  #{fetched.id} state={fetched.state}")

updated = adapter.update(issue.id, IssueUpdate(title="Updated title"))
print(f"Updated:  #{updated.id} — {updated.title}")

adapter.delete(issue.id)
print("Deleted.  SQLite CRUD complete.")

# --- GitHub: same interface, different backend ---
# print("\n=== GitHub ===")
# repo = os.getenv("GITHUB_REPO", "")

# if not repo:
#     print("Skipped (set GITHUB_REPO to enable; token auto-resolved from ZENVE_GH_TOKEN or gh CLI).")
# else:
#     gh = GitHubIssueAdapter(GitHubIssueConfig(repo=repo))
#     registry.add(gh)

#     if not gh.health_check():
#         print("GitHub health check failed — check token and repo.")
#     else:
#         new = gh.create(IssueCreate(title="[zenve-issues example]", body="Created by zenve_issues_usage.py"))
#         print(f"Created:  #{new.id} — {new.title}")

#         issues = gh.list(IssueListFilter(state="open", limit=5))
#         print(f"Listed:   {len(issues)} open issue(s) (limit=5)")

#         fetched = gh.get(new.id)
#         print(f"Fetched:  #{fetched.id} state={fetched.state}")

#         updated = gh.update(new.id, IssueUpdate(title="[zenve-issues example] updated"))
#         print(f"Updated:  #{updated.id} — {updated.title}")

#         gh.delete(new.id)  # closes the issue (GitHub has no delete endpoint)
#         print("Deleted:  issue closed (delete = close on GitHub). GitHub CRUD complete.")
