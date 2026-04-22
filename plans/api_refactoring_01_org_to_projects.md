# API Refactor 01 — Rename Organizations → Projects

## Goal

Rename `organizations` to `projects` across the entire server codebase. One project = one GitHub repo. This is a foundational rename that everything else builds on.

## Changes

### DB models (`packages/db/src/zenve_db/models.py`)
- Rename `Organization` class → `Project` (table `projects`)
- Drop columns: `base_path`, `redis_worker_url`
- Add columns: `github_installation_id: int | None`, `github_repo: str | None` (format `owner/name`), `github_default_branch: str | None`
- On `Membership`: rename `org_id` → `project_id`, relationship `organization` → `project`
- On `ApiKeyRecord`: rename `org_id` → `project_id`, relationship `organization` → `project`

### Pydantic models (`packages/models/src/zenve_models/`)
- Rename `org.py` → `project.py`
- Rename `OrgCreate/Update/Response` → `ProjectCreate/Update/Response`
- Drop `base_path`/`redis_worker_url` fields
- Add `ProjectGitHubConnect(installation_id, repo)` request model
- Update `__init__.py` exports

### Services (`packages/services/src/zenve_services/`)
- Rename `org.py` → `project.py`; `OrgService` → `ProjectService`
- Creation becomes pure DB insert + owner membership (drop filesystem bootstrap: `base_path`, git init, template copy)
- `api_key_auth.py`: rename `get_current_org` → `get_current_project`; return type `(Project, ApiKeyRecord)`
- `api_key.py`: reparent FKs from `org_id` to `project_id`
- `membership.py`: rename fields/params (`org_id` → `project_id`)
- Update `__init__.py` exports

### Routes (`apps/api/src/api/routes/`)
- Rename `org.py` → `project.py`; prefix `/api/v1/projects`
- `api_key.py`: nest under `/api/v1/projects/{id}/api-keys`
- Update `__init__.py` and `main.py` imports + `include_router` calls

### Config (`packages/config/src/zenve_config/settings.py`)
- Remove dead settings: `data_dir`, `templates_dir`, `gateway_url`, `setup_token`, `redis_url`, `redis_password`

## Dependencies
- None — this can be done first
- Note: UI will break (16 files call `/orgs`). Either bundle a UI PR or add a temporary `/orgs` alias

## Verification
1. `rm server/zenve.db && just dev`
2. `POST /api/v1/auth/signup` → JWT
3. `POST /api/v1/projects` with JWT → new project row, no filesystem side-effects
4. Existing API key auth still works with `project_id` FK
