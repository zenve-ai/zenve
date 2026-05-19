"""
zenve-issues basic usage.

SQLite runs automatically (no auth needed).
GitHub requires GITHUB_REPO env var; token is auto-resolved from
ZENVE_GH_TOKEN env var or `gh auth token`.

Usage (from server/):
    uv run python examples/zenve_issues_usage.py
"""

from zenve_issues import (
    CommentCreate,
    CommentUpdate,
    IssueAdapterRegistry,
    IssueCreate,
    IssueListFilter,
    IssueUpdate,
    SQLiteIssueAdapter,
    SQLiteIssueConfig,
)

registry = IssueAdapterRegistry()
registry.add(SQLiteIssueAdapter(SQLiteIssueConfig(db_path="./test.db")))

# --- SQLite: full CRUD against an in-memory database ---
print("=== SQLite ===")
adapter = registry.get("sqlite")

issue = adapter.create(IssueCreate(title="My first issue", body="Hello from zenve-issues"))
print(f"Created:  #{issue.id} — {issue.title}")

issues = adapter.list(IssueListFilter(state="open"))
print(f"Listed:   {len(issues)} open issue(s)")

for i in issues:
    print(f"  #{i.id} — {i.title}")


fetched = adapter.get(issue.id)
print(f"Fetched:  #{fetched.id} state={fetched.state}")

updated = adapter.update(issue.id, IssueUpdate(title="Updated title"))
print(f"Updated:  #{updated.id} — {updated.title}")

# --- Comments ---
comment = adapter.add_comment(issue.id, CommentCreate(body="First comment"))
print(f"Comment:  #{comment.id} on issue #{comment.issue_id} — {comment.body!r}")

comments = adapter.list_comments(issue.id)
print(f"Listed:   {len(comments)} comment(s) on issue #{issue.id}")

fetched_comment = adapter.get_comment(comment.id)
print(f"Fetched:  comment #{fetched_comment.id} — {fetched_comment.body!r}")

# updated_comment = adapter.update_comment(comment.id, CommentUpdate(body="Updated comment"))
# print(f"Updated:  comment #{updated_comment.id} — {updated_comment.body!r}")

# adapter.delete_comment(comment.id)
# print(f"Deleted:  comment #{comment.id}")

# adapter.delete(issue.id)
# print("Deleted.  SQLite CRUD complete.")

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
