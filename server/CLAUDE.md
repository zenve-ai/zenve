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

### Services (`packages/services/`)
- All business logic lives here
- Receive `db: Session` via constructor, never import `get_db` directly
- Dependency functions (`get_*_service`) go in `zenve_services/__init__.py`

### Models (`packages/models/`)
- All Pydantic models go here — never define them inside `apps/api/`
- Shared freely across routes, services, and utils

### Utils (`packages/utils/`)
- Pure stateless helpers: hashing, JWT, `get_current_user` FastAPI dependency
- No business logic

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

## Violations to Flag

- `from zenve_db` imported inside any `apps/api/routes/` file
- `get_db` used directly in a route handler
- Pydantic models defined inside `apps/api/`
- Business logic (db queries, conditionals) inside route handlers

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

1. **Pydantic model** → `packages/models/src/zenve_models/{domain}.py`
2. **ORM model** → `packages/db/src/zenve_db/models.py`
3. **Service** → `packages/services/src/zenve_services/{domain}.py`
4. **Dependency function** → `packages/services/src/zenve_services/__init__.py`
5. **Route** → `apps/api/src/api/routes/{domain}.py` (thin wrapper)
6. **Register router** → `apps/api/src/api/routes/__init__.py` + `main.py`

## Adding a New Package

1. Create `packages/{name}/pyproject.toml` with name `zenve-{name}`
2. Create `packages/{name}/src/zenve_{name}/__init__.py`
3. Add to workspace root `pyproject.toml`: `[tool.uv.sources]` entry
4. Run `uv sync`
