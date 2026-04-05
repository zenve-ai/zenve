# CLAUDE.md

Architecture and development rules for this FastAPI project.

## Project Structure

```
src/zenve/
├── agents/          # AI agents (LLM reasoning units)
├── api/
│   ├── routes/      # Thin HTTP handlers only
│   ├── lifespan.py  # Startup/shutdown
│   └── __init__.py
├── config/          # Settings (pydantic-settings)
├── db/              # SQLAlchemy engine, session, ORM models
├── models/          # Pydantic models (shared across routes, agents, services)
├── services/        # Business logic
│   ├── __init__.py  # Dependency functions (get_*_service)
│   └── auth.py      # One file per domain
└── utils/           # Stateless helpers (hashing, JWT, etc.)
```

## Layer Rules

### Routes (`api/routes/`)
- Thin wrappers only — no business logic, no db queries
- Only call services via `Depends()`
- Import services from `services` not from other routes

### Services (`services/`)
- All business logic lives here
- Receive `db: Session` in `__init__`, never import `get_db` directly
- Can be used by routes AND agents
- Dependency functions (`get_*_service`) go in `services/__init__.py` — not in route files

### Models (`models/`)
- All Pydantic models go here — never inside `api/`
- Shared freely across routes, services, and agents

### Agents (`agents/`)
- AI reasoning units — call LLMs, use tools
- Receive services via constructor, never import `db` or `get_db` directly
- Do not contain business logic — delegate to services

### DB (`db/`)
- `database.py` — engine, session, `get_db`
- `models.py` — SQLAlchemy ORM models using `Mapped` / `mapped_column`
- Only imported in `services/` and `utils/`

## Violations to Flag

- `from zenve.db` imported inside any `api/routes/` file
- `get_db` used directly in a route handler
- Pydantic models defined inside `api/`
- `get_*_service` functions defined inside route files
- Business logic (db queries, data conditionals) inside route handlers
- Agents importing `db` or `Session` directly

## Scratchpad (`scratchpad/`)

Your workspace for planning, research, and intermediate artifacts. Use it to:
- Store architecture docs, design notes, and implementation chunks
- Write draft code or pseudocode before committing to `src/`
- Keep context files that inform feature work (e.g. `scratchpad/chunks/`)
- Save any information you need to persist across conversations

This directory is **not production code** — it is never imported or deployed. Feel free to create, update, or reorganize files here as needed.

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

1. **Model** → `models/{domain}.py`
2. **ORM model** → `db/models.py`
3. **Service** → `services/{domain}.py`
4. **Dependency function** → `services/__init__.py`
5. **Route** → `api/routes/{domain}.py` (thin wrapper)
6. **Register router** → `api/routes/__init__.py` + `main.py`
7. **Agent** (if AI needed) → `agents/{domain}.py`, inject service via constructor


## Using Custom Agents

When asked to "use the {name} agent", follow these steps:
0. Spawn a subagent to handle the entire task below
1. Read `agents/{name}/AGENTS.md`
2. Follow all instructions in that file exactly
3. Apply the agent's rules to the current task