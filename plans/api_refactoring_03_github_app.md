# API Refactor 03 — GitHub App Integration

## Goal

Add GitHub App support so the API can read from and write to user repos. This is the infrastructure layer that the repo-backed agent API (plan 04) builds on.

## New config (`packages/config/src/zenve_config/settings.py`)
- Add `github_app_id: int | None`
- Add `github_app_private_key: str | None`
- Add `github_webhook_secret: str | None`
- Add `zenve_webhook_secret: str | None`

## New: GitHub utils (`packages/utils/src/zenve_utils/github.py`)
- `mint_installation_token(installation_id) -> str` — JWT-sign app assertion, POST `/app/installations/{id}/access_tokens`, cache 5-min TTL
- `get_repo_file(installation_id, repo, path, ref=None) -> bytes` — contents API
- `list_repo_dir(installation_id, repo, path, ref=None) -> list[dict]`
- `commit_tree(installation_id, repo, branch, files: dict[str, bytes | None], message: str) -> str` — create blobs → tree → commit → update ref. `None` value = deletion. Returns new commit SHA
- `verify_hmac_sha256(body, signature, secret) -> bool` — shared for GitHub + Zenve webhooks

## New: GitHub service (`packages/services/src/zenve_services/github.py`)
- `GitHubService`
  - `connect_project(project, installation_id, repo)` — validate app can read repo, then persist
  - `disconnect(project)` — clear GitHub fields

## New: Repo writer service (`packages/services/src/zenve_services/repo_writer.py`)
- `RepoWriterService` wraps `commit_tree` for higher-level ops:
  - `scaffold_agent(project, agent_slug, rendered_files, commit_message)`
  - `delete_agent(project, agent_slug)`
  - `write_file(project, agent_slug, relpath, content)`
  - Path-traversal guards before calling `commit_tree`

## New routes (add to `apps/api/src/api/routes/project.py`)
- `POST /api/v1/projects/{id}/github/connect` — body `{installation_id, repo}`, validates + persists
- `DELETE /api/v1/projects/{id}/github/disconnect` — clears GitHub fields

## Dependencies
- Requires plan 01 (projects table with `github_*` columns)
- Requires plan 02 (clean codebase, no dead imports)

## Verification
1. Configure GitHub App credentials in env
2. Install app on a test repo, note `installation_id`
3. `POST /api/v1/projects/{id}/github/connect {installation_id, repo}` → 200, fields populated
4. `DELETE /api/v1/projects/{id}/github/disconnect` → fields nulled
