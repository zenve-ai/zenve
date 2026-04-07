# fastapi-monorepo-setup

Scaffolds a production-ready FastAPI monorepo using `uv` workspaces.

## What it creates

Given a project name (e.g. `myapp`), scaffolds:

```
myapp/
├── apps/api/          ← FastAPI app with JWT auth routes
└── packages/
    ├── config/        ← pydantic-settings (myapp-config)
    ├── db/            ← SQLAlchemy engine + ORM models (myapp-db)
    ├── models/        ← Pydantic request/response models (myapp-models)
    ├── utils/         ← JWT, hashing, get_current_user (myapp-utils)
    └── services/      ← Business logic (myapp-services)
```

## Trigger phrases

- "create a new fastapi monorepo"
- "setup a monorepo fastapi project"
- "scaffold a fastapi monorepo"
- "new fastapi project with packages"
- "initialize a fastapi monorepo"
- "add a new app to a fastapi monorepo"

## Tech stack

- **FastAPI** + **uvicorn**
- **uv workspaces** (single `uv.lock` at root)
- **SQLAlchemy 2** + SQLite (default) / PostgreSQL
- **JWT** via `python-jose` + `bcrypt`
- **Pydantic v2** + `pydantic-settings`
- **Docker** with fast startup (`uv sync --package` + direct venv CMD)
- **just** task runner

## Package dependency chain

```
myapp-config  (no internal deps)
myapp-db      → myapp-config
myapp-models  → (pydantic only)
myapp-utils   → myapp-config, myapp-db
myapp-services → myapp-db, myapp-models, myapp-utils
apps/api       → all packages above
```

## Quick start (after scaffolding)

```bash
uv sync
cp .env.example .env
just dev
```

API at `http://localhost:8000` — `POST /auth/signup` returns a JWT.
