# CLAUDE.md

Architecture and development rules for this FastAPI monorepo.

## Sub-project docs

- [apps/cli/CLAUDE.md](apps/cli/CLAUDE.md) — CLI app: structure, layer rules, `.zenve/` convention, env vars, run flow
- [apps/runtime/CLAUDE.md](apps/runtime/CLAUDE.md) — Runtime daemon: local FastAPI server (port 8001) exposing workspaces and runs over HTTP
- [packages/engine/CLAUDE.md](packages/engine/CLAUDE.md) — Engine: self-contained library that executes a run against a `.zenve/` repo

## Monorepo Structure

```
server/
├── apps/
│   ├── api/          # Deployable FastAPI application
│   │   └── src/api/
│   │       ├── config.py
│   │       ├── db/        # SQLAlchemy engine, session, ORM models
│   │       ├── models/    # Pydantic request/response models
│   │       ├── utils/     # JWT, hashing, GitHub helpers
│   │       ├── services/  # Business logic
│   │       ├── routes/    # Thin HTTP handlers only
│   │       ├── lifespan.py
│   │       └── main.py
│   ├── cli/          # Typer CLI — runs agents against a GitHub repo
│   │   └── src/zenve_cli/
│   │       ├── config.py
│   │       ├── models/
│   │       ├── services/
│   │       └── utils/
│   └── runtime/      # Local FastAPI daemon (port 8001)
│       └── src/runtime/
│           ├── models/
│           ├── services/
│           └── routes/
└── packages/
    ├── engine/        # Run executor — used by CLI and runtime
    └── adapters/      # Adapter types: RunContext, RunResult, *Config, BaseAdapter
```

Each app is **self-contained** — it carries its own `config.py`, `models/`, `services/`, and `utils/`. Apps never import from each other.

## Layer Rules

### Routes (`apps/api/src/api/routes/`)
- Thin wrappers only — no business logic, no db queries
- Only call services via `Depends()`
- Import from `api.services`, never from `api.db` directly
- No helper functions — move any utility logic to `api.utils`

### Services (`apps/api/src/api/services/`)
- All business logic lives here
- Receive `db: Session` via constructor, never import `get_db` directly
- Dependency functions (`get_*_service`) go in `api/services/__init__.py`
- **Never raise `HTTPException`** — services are HTTP-agnostic. Raise domain exceptions from `api.models.errors` instead (`NotFoundError`, `ConflictError`, `ValidationError`, `ExternalError`, `RateLimitError`, `AuthError`). FastAPI exception handlers in `apps/api/src/api/main.py` convert these to HTTP responses.

### Models (`apps/api/src/api/models/`)
- All Pydantic models for the API go here — never define them inside `routes/`
- Used freely by routes, services, and utils within the same app

### Utils (`apps/api/src/api/utils/`)
- Pure stateless helpers: hashing, JWT, `get_current_user` FastAPI dependency (JWT auth)
- No business logic

### DB (`apps/api/src/api/db/`)
- `database.py` — engine, session, `get_db`
- `models.py` — SQLAlchemy ORM models using `Mapped` / `mapped_column`
- Only imported by `services/` and `utils/`

## Package Dependency Chain

```
zenve-engine   → zenve-adapters    # the run executor — used by CLI and runtime
zenve-adapters → pydantic          # RunContext, RunResult, all *Config types
apps/api       → zenve-adapters    # uses adapter config types for agent management
apps/cli       → zenve-engine, zenve-adapters
apps/runtime   → zenve-engine
```

## Authentication & Authorization

Two auth systems coexist — use the right one for each context:

### JWT Auth (User sessions)
- Users log in via `/auth/login` or `/auth/signup`, receive a JWT token (24h TTL)
- Dependency: `get_current_user()` from `zenve_utils.auth` → returns `UserRecord`
- **Used for:** Organization CRUD (`/api/v1/orgs`) — any user-facing operation

### API Key Auth (Programmatic access)
- Orgs have API keys (`zv_live_*` prefix), stored as bcrypt hashes
- Dependency: `get_current_org()` from `zenve_services.api_key_auth` → returns `(Organization, ApiKeyRecord)`
- Scope-based access: `require_scope("agents:write")` for fine-grained control
- **Used for:** Agent routes (`/api/v1/agents`), API key management (`/api/v1/api-keys`)

### User–Org Membership
- `Membership` join table links users to orgs with roles: `owner`, `admin`, `member`
- Org creation requires a logged-in user who becomes the `owner`
- `MembershipService.require_membership()` — verifies user belongs to org (403 if not)
- `MembershipService.require_role()` — verifies user has specific role(s) (403 if not)
- Org update restricted to `owner` role

### When to use which
| Route context | Auth dependency | Notes |
|---|---|---|
| Org CRUD (`/api/v1/orgs`) | `get_current_user` (JWT) | Membership checked via `MembershipService` |
| Agents (`/api/v1/agents`) | `get_current_org` + `require_scope` (API key) | For programmatic/agent access |
| API keys (`/api/v1/api-keys`) | `get_current_org` (API key) | Manage keys within an org |

## Naming Rules

- **No underscore prefix on functions** — never write `def _my_func`. Use plain names (`def my_func`) even for module-private or helper functions.

## Violations to Flag

- `from api.db` imported inside any `apps/api/routes/` file
- `get_db` used directly in a route handler
- Pydantic models defined inside `routes/`
- Business logic (db queries, conditionals) inside route handlers
- Helper functions defined inside route files — move to `utils/`
- `from fastapi import HTTPException` inside any `services/` file — use domain errors instead
- Cross-app imports: one app importing from another app's namespace
- Any import of deleted packages: `zenve_config`, `zenve_db`, `zenve_models`, `zenve_utils`, `zenve_services`

## Development Commands

```bash
just dev          # start with hot reload
just start        # start production mode
just lint         # ruff check
just lint-fix     # ruff check --fix
just format       # ruff format
just typecheck    # pyright

just docker-build # build image
just docker-up    # start container
just docker-down  # stop container
just docker-logs  # tail logs
```

## Adding a New Feature (API)

1. **Pydantic Model** → `apps/api/src/api/models/{domain}.py`
2. **ORM Model** → `apps/api/src/api/db/models.py`
3. **Service** → `apps/api/src/api/services/{domain}.py`
4. **Dependency function** → `apps/api/src/api/services/__init__.py`
5. **Route** → `apps/api/src/api/routes/{domain}.py` (thin wrapper)
6. **Register Router** → `apps/api/src/api/routes/__init__.py` + `main.py`
