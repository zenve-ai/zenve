# fastapi-architect

Claude Code skill that audits any FastAPI project against a clean layered architecture.

## Install

```bash
npx skills add ghalex/skills --skill fastapi-architect
```

## Usage

Navigate to any FastAPI project and ask Claude:

> "review my routes"
> "check architecture"
> "audit this project"
> "does this follow the fastapi rules"
> "review my code structure"

## What it checks

**Routes** — no business logic, no db queries, no inline dependency functions

**Services** — business logic only here, `get_*_service` in `services/__init__.py`

**Models** — Pydantic models outside `api/`, ORM models use SQLAlchemy 2.x `Mapped` style

**Agents** — no direct db access, services injected via constructor

**General** — CORS, uvicorn config, lifespan typing

## Output

```
## Architecture Review

### ✅ Passing
- Models correctly placed in models/
- ...

### ❌ Violations
#### src/myapi/api/routes/users.py
- **Rule:** No db queries inside route handlers
- **Found:** db.query(UserRecord)... called directly in route
- **Fix:** Move to UserService.get_user() and inject via Depends(get_user_service)

### Summary
2 violations found in 1 file.
```
