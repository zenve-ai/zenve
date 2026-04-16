# CLAUDE.md

Architecture and development rules for this FastAPI monorepo.

## Monorepo Structure

```
server/
├── apps/api/         # Deployable FastAPI application
│   └── src/api/
│       ├── routes/   # Thin HTTP handlers only
│       ├── lifespan.py
│       └── main.py
└── packages/
    ├── config/       # Settings (pydantic-settings)
    ├── db/           # SQLAlchemy engine, session, ORM models
    ├── models/       # Pydantic request/response models
    ├── services/     # Business logic
    └── utils/        # Stateless helpers (JWT, hashing, auth deps)
```

## Layer Rules

### Routes (`apps/api/src/api/routes/`)
- Thin wrappers only — no business logic, no db queries
- Only call services via `Depends()`
- Import from `zenve_services`, never from `zenve_db` directly
- No helper functions — move any utility logic to `zenve_utils`

### Services (`packages/services/`)
- All business logic lives here
- Receive `db: Session` via constructor, never import `get_db` directly
- Dependency functions (`get_*_service`) go in `zenve_services/__init__.py`

### Models (`packages/models/`)
- All Pydantic models go here — never define them inside `apps/api/`
- Shared freely across routes, services, and utils

### Utils (`packages/utils/`)
- Pure stateless helpers: hashing, JWT, `get_current_user` FastAPI dependency (JWT auth)
- No business logic
- **Test helpers** — shared test utilities (mock factories, fake data builders) go in `packages/utils/src/zenve_utils/testing.py`, not in individual test files or conftest.py

### DB (`packages/db/`)
- `database.py` — engine, session, `get_db`
- `models.py` — SQLAlchemy ORM models using `Mapped` / `mapped_column`
- Only imported by `services/` and `utils/`

## Package Dependency Chain

```
zenve-config  (no internal deps)
zenve-db      → zenve-config
zenve-models  → (pydantic only)
zenve-utils   → zenve-config, zenve-db
zenve-services → zenve-db, zenve-models, zenve-utils
apps/api          → all packages above
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

- `from zenve_db` imported inside any `apps/api/routes/` file
- `get_db` used directly in a route handler
- Pydantic models defined inside `apps/api/`
- Business logic (db queries, conditionals) inside route handlers
- Helper functions defined inside `apps/api/routes/` — move to `zenve_utils`

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

## Adding a New Feature

1. **Pydantic Model** → `packages/models/src/zenve_models/{domain}.py`
2. **ORM Model** → `packages/db/src/zenve_db/models.py`
3. **Service** → `packages/services/src/zenve_services/{domain}.py`
4. **Dependency function** → `packages/services/src/zenve_services/__init__.py`
5. **Route** → `apps/api/src/api/routes/{domain}.py` (thin wrapper)
6. **Register Router** → `apps/api/src/api/routes/__init__.py` + `main.py`

## Architecture Documentation

@../docs/architecture/00-overview.md

Project architecture is documented in `../docs/architecture/` using a numbered chunk system:

```
docs/architecture/
    00-overview.md          # Master index — entry point, lists every chunk with dependencies and deliverables
    01-organizations-crud.md
    02-api-key-auth.md
    ...
    NN-feature-name.md      # One file per feature/domain boundary
```

- **`00-overview.md`** is always the entry point. It contains a table of every chunk with its number, name, dependencies, and key deliverables.
- **Chunk files (`01–NN`)** each describe a single feature or domain boundary.

**IMPORTANT:** Whenever a new feature is added or an architectural change is made, you **must** update the relevant chunk file(s) in `docs/architecture/` and keep `00-overview.md` in sync. Do not leave docs stale after implementation changes.

### Chunk Template

When creating a new chunk file, use this structure:

```markdown
# Chunk NN — Feature Name

## Goal
One paragraph: what this feature does and why it exists.

## Depends On
- Chunk XX — Name (what it provides to this feature)
- Chunk YY — Name

## Referenced By
- Chunk ZZ — Name (what this feature provides to it)

## Deliverables

### 1. ORM Model — `db/models.py`
Table schema, column definitions, relationships.

### 2. Pydantic Models — `models/{domain}.py`
Request/response schemas with field descriptions.

### 3. Service — `services/{domain}.py`
Class signature, public methods, key business rules.

### 4. Dependency Function — `services/__init__.py`
The `get_*_service` factory.

### 5. Routes — `api/routes/{domain}.py`
Endpoint table (method, path, description).

### 6. Agent Integration — `agents/{domain}.py` (if applicable)
How agents interact with this feature.

## Config
Environment variables or settings this feature introduces.

## Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|

## Notes
Edge cases, open questions, things to revisit.

## Change Log
| Date | Change | Reason |
|------|--------|--------|
```

## Adding a New Package

1. Create `packages/{name}/pyproject.toml` with name `zenve-{name}`
2. Create `packages/{name}/src/zenve_{name}/__init__.py`
3. Add to workspace root `pyproject.toml`: `[tool.uv.sources]` entry
4. Run `uv sync`
