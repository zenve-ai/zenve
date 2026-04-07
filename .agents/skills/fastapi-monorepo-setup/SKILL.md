---
name: fastapi-monorepo-setup
description: Scaffolds a production-ready FastAPI monorepo with uv workspaces, 5 shared packages (config, db, models, utils, services), JWT auth, SQLAlchemy, and Docker support. Use when asked to "create a new fastapi monorepo", "setup a monorepo fastapi project", "scaffold a fastapi monorepo", "new fastapi project with packages", "initialize a fastapi monorepo", or "add a new app to a fastapi monorepo".
version: 1.0.0
---

# FastAPI Monorepo Setup

Scaffold a complete, production-ready FastAPI monorepo using `uv` workspaces. Ask the user for the **project name** if not provided (e.g. `myapp`). Use it throughout as `{project}`.

- Package names use **hyphens**: `{project}-config`, `{project}-db`, etc.
- Python module names use **underscores**: `{project}_config`, `{project}_db`, etc.

---

## Project Structure

Create all files exactly as shown. Replace `{project}` with the actual project name.

```
{project}/
├── apps/
│   └── api/
│       ├── src/api/
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── auth.py
│       │   │   └── core.py
│       │   ├── __init__.py
│       │   ├── lifespan.py
│       │   └── main.py
│       ├── pyproject.toml
│       └── Dockerfile
├── packages/
│   ├── config/
│   │   ├── src/{project}_config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   └── pyproject.toml
│   ├── db/
│   │   ├── src/{project}_db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   └── pyproject.toml
│   ├── models/
│   │   ├── src/{project}_models/
│   │   │   ├── __init__.py
│   │   │   └── auth.py
│   │   └── pyproject.toml
│   ├── services/
│   │   ├── src/{project}_services/
│   │   │   ├── __init__.py
│   │   │   └── auth.py
│   │   └── pyproject.toml
│   └── utils/
│       ├── src/{project}_utils/
│       │   ├── __init__.py
│       │   └── auth.py
│       └── pyproject.toml
├── pyproject.toml
├── justfile
├── docker-compose.yml
├── CLAUDE.md
├── .env.example
└── .python-version
```

---

## File Templates

### `.python-version`
```
3.13
```

### `.env.example`
```
SECRET_KEY=changeme-use-a-long-random-string
SQLITE_DATABASE_URL={project}.db
PG_DATABASE_URL=postgresql://user:password@localhost:5432/{project}
```

### `pyproject.toml` (workspace root)
```toml
[project]
name = "{project}-workspace"
version = "0.1.0"
description = "{project} monorepo workspace"
requires-python = ">=3.13"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
only-include = ["README.md"]

[tool.uv.workspace]
members = [
    "apps/api",
    "packages/*",
]

[tool.uv.sources]
{project}-config = { workspace = true }
{project}-db = { workspace = true }
{project}-models = { workspace = true }
{project}-utils = { workspace = true }
{project}-services = { workspace = true }

[dependency-groups]
dev = [
    "pyright>=1.1.407",
    "ruff>=0.11.0",
]

[tool.ruff]
line-length = 100

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = [
    "{project}_config",
    "{project}_db",
    "{project}_models",
    "{project}_utils",
    "{project}_services",
]
```

### `justfile`
```just
# Application

dev:
    API_RELOAD=true uv run api-start

start:
    uv run api-start

# Package management

install:
    uv sync

add-to-api package:
    uv add --package {project}-api {{package}}

add-to-pkg pkg package:
    uv add --package {{pkg}} {{package}}

update:
    uv lock --upgrade
    uv sync

# Docker

docker-build:
    docker build -f apps/api/Dockerfile -t {project}-api:latest .

docker-up:
    docker compose up -d

docker-down:
    docker compose down

docker-logs:
    docker compose logs -f

# Code quality

format:
    uv run ruff format .

lint path=".":
    uv run ruff check {{path}}

lint-fix path=".":
    uv run ruff check --fix {{path}}

typecheck path=".":
    uv run pyright {{path}}
```

### `docker-compose.yml`
```yaml
services:
  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    image: {project}-api:latest
    container_name: {project}-api
    ports:
      - "8000:8000"
    restart: unless-stopped
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - SQLITE_DATABASE_URL=${SQLITE_DATABASE_URL}
      - PG_DATABASE_URL=${PG_DATABASE_URL}
```

### `CLAUDE.md`
```markdown
# CLAUDE.md

Architecture and development rules for this FastAPI monorepo.

## Monorepo Structure

\`\`\`
{project}/
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
\`\`\`

## Layer Rules

### Routes (`apps/api/src/api/routes/`)
- Thin wrappers only — no business logic, no db queries
- Only call services via `Depends()`
- Import from `{project}_services`, never from `{project}_db` directly

### Services (`packages/services/`)
- All business logic lives here
- Receive `db: Session` via constructor, never import `get_db` directly
- Dependency functions (`get_*_service`) go in `{project}_services/__init__.py`

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

\`\`\`
{project}-config  (no internal deps)
{project}-db      → {project}-config
{project}-models  → (pydantic only)
{project}-utils   → {project}-config, {project}-db
{project}-services → {project}-db, {project}-models, {project}-utils
apps/api          → all packages above
\`\`\`

## Violations to Flag

- `from {project}_db` imported inside any `apps/api/routes/` file
- `get_db` used directly in a route handler
- Pydantic models defined inside `apps/api/`
- Business logic (db queries, conditionals) inside route handlers

## Development Commands

\`\`\`bash
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
\`\`\`

## Adding a New Feature

1. **Pydantic model** → `packages/models/src/{project}_models/{domain}.py`
2. **ORM model** → `packages/db/src/{project}_db/models.py`
3. **Service** → `packages/services/src/{project}_services/{domain}.py`
4. **Dependency function** → `packages/services/src/{project}_services/__init__.py`
5. **Route** → `apps/api/src/api/routes/{domain}.py` (thin wrapper)
6. **Register router** → `apps/api/src/api/routes/__init__.py` + `main.py`

## Adding a New Package

1. Create `packages/{name}/pyproject.toml` with name `{project}-{name}`
2. Create `packages/{name}/src/{project}_{name}/__init__.py`
3. Add to workspace root `pyproject.toml`: `[tool.uv.sources]` entry
4. Run `uv sync`
```

---

## Package Templates

### `packages/config/pyproject.toml`
```toml
[project]
name = "{project}-config"
version = "0.1.0"
description = "{project} configuration package"
requires-python = ">=3.13"
dependencies = [
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{project}_config"]
```

### `packages/config/src/{project}_config/__init__.py`
```python
from .settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
```

### `packages/config/src/{project}_config/settings.py`
```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    secret_key: str
    sqlite_database_url: str = "{project}.db"
    pg_database_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

### `packages/db/pyproject.toml`
```toml
[project]
name = "{project}-db"
version = "0.1.0"
description = "{project} database models and connection"
requires-python = ">=3.13"
dependencies = [
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "{project}-config",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{project}_db"]

[tool.uv.sources]
{project}-config = { workspace = true }
```

### `packages/db/src/{project}_db/__init__.py`
```python
from .database import Base, Session, engine, get_db
from .models import UserRecord

__all__ = ["Base", "Session", "engine", "get_db", "UserRecord"]
```

### `packages/db/src/{project}_db/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from {project}_config.settings import settings


def create_sqlite_engine(path: str | None = None):
    if path is None:
        path = settings.sqlite_database_url
    if not path:
        raise ValueError("SQLITE_DATABASE_URL is not set.")
    return create_engine(f"sqlite:///{path}")


def create_postgres_engine(connection_string: str | None = None):
    if connection_string is None:
        connection_string = settings.pg_database_url
    if not connection_string:
        raise ValueError("PG_DATABASE_URL is not set.")
    return create_engine(connection_string)


Base = declarative_base()

engine = create_sqlite_engine()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
```

### `packages/db/src/{project}_db/models.py`
```python
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from {project}_db.database import Base


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

---

### `packages/models/pyproject.toml`
```toml
[project]
name = "{project}-models"
version = "0.1.0"
description = "{project} shared Pydantic models"
requires-python = ">=3.13"
dependencies = [
    "pydantic[email]>=2.10.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{project}_models"]
```

### `packages/models/src/{project}_models/__init__.py`
```python
from .auth import LoginRequest, SignupRequest, TokenResponse, UserResponse

__all__ = ["LoginRequest", "SignupRequest", "TokenResponse", "UserResponse"]
```

### `packages/models/src/{project}_models/auth.py`
```python
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
```

---

### `packages/utils/pyproject.toml`
```toml
[project]
name = "{project}-utils"
version = "0.1.0"
description = "{project} utility functions"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115.0",
    "bcrypt>=4.0",
    "python-jose[cryptography]>=3.5.0",
    "{project}-config",
    "{project}-db",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{project}_utils"]

[tool.uv.sources]
{project}-config = { workspace = true }
{project}-db = { workspace = true }
```

### `packages/utils/src/{project}_utils/__init__.py`
```python
from .auth import create_token, get_current_user, hash_password, verify_password

__all__ = ["create_token", "get_current_user", "hash_password", "verify_password"]
```

### `packages/utils/src/{project}_utils/auth.py`
```python
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from {project}_config.settings import settings
from {project}_db.database import get_db
from {project}_db.models import UserRecord

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UserRecord:
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization",
        )
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user_id = int(user_id)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

---

### `packages/services/pyproject.toml`
```toml
[project]
name = "{project}-services"
version = "0.1.0"
description = "{project} business logic services"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115.0",
    "sqlalchemy>=2.0.0",
    "{project}-db",
    "{project}-models",
    "{project}-utils",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{project}_services"]

[tool.uv.sources]
{project}-config = { workspace = true }
{project}-db = { workspace = true }
{project}-models = { workspace = true }
{project}-utils = { workspace = true }
```

### `packages/services/src/{project}_services/__init__.py`
```python
from fastapi import Depends
from sqlalchemy.orm import Session

from {project}_db.database import get_db
from {project}_services.auth import AuthService


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)
```

### `packages/services/src/{project}_services/auth.py`
```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from {project}_db.models import UserRecord
from {project}_models import LoginRequest, SignupRequest, TokenResponse, UserResponse
from {project}_utils.auth import create_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def signup(self, body: SignupRequest) -> TokenResponse:
        if self.db.query(UserRecord).filter(UserRecord.email == body.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        user = UserRecord(
            email=body.email,
            name=body.name,
            password_hash=hash_password(body.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return TokenResponse(
            access_token=create_token(user.id),
            user=UserResponse.model_validate(user),
        )

    def login(self, body: LoginRequest) -> TokenResponse:
        user = self.db.query(UserRecord).filter(UserRecord.email == body.email).first()

        if (
            not user
            or not user.password_hash
            or not verify_password(body.password, user.password_hash)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        return TokenResponse(
            access_token=create_token(user.id),
            user=UserResponse.model_validate(user),
        )
```

---

## App Templates

### `apps/api/pyproject.toml`
```toml
[project]
name = "{project}-api"
version = "0.1.0"
description = "{project} FastAPI application"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "{project}-config",
    "{project}-db",
    "{project}-models",
    "{project}-utils",
    "{project}-services",
]

[project.scripts]
api-start = "api.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.hatch.build.targets.wheel.sources]
"src" = ""

[tool.uv.sources]
{project}-config = { workspace = true }
{project}-db = { workspace = true }
{project}-models = { workspace = true }
{project}-utils = { workspace = true }
{project}-services = { workspace = true }
```

### `apps/api/Dockerfile`
```dockerfile
# Build from workspace root: docker build -f apps/api/Dockerfile -t {project}-api .
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy workspace root config
COPY pyproject.toml uv.lock ./

# Copy all packages and the API app
COPY packages/ packages/
COPY apps/api/ apps/api/

# Install only the API app and its workspace dependencies
RUN uv sync --frozen --no-dev --no-cache --compile-bytecode --package {project}-api

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD [".venv/bin/api-start"]
```

### `apps/api/src/api/__init__.py`
```python
```

### `apps/api/src/api/main.py`
```python
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.lifespan import lifespan
from api.routes import auth_router, core_router

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Disposition"],
)

app.include_router(core_router)
app.include_router(auth_router)


def main():
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    if reload:
        uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
```

### `apps/api/src/api/lifespan.py`
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from {project}_db.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 60)
    print(f"Starting {project} API")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified")

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Application may not function correctly!")

    yield

    engine.dispose()
    print("{project} API shutdown complete")
```

### `apps/api/src/api/routes/__init__.py`
```python
from .auth import router as auth_router
from .core import router as core_router

__all__ = ["auth_router", "core_router"]
```

### `apps/api/src/api/routes/core.py`
```python
from fastapi import APIRouter

router = APIRouter(tags=["core"])


@router.get("/")
def root():
    return {"ok": True, "message": "{project} API is running", "version": "0.1.0"}


@router.get("/healthz")
def healthz():
    return {"ok": True, "service": "{project}-api", "version": "0.1.0"}
```

### `apps/api/src/api/routes/auth.py`
```python
from fastapi import APIRouter, Depends, status

from {project}_models import LoginRequest, SignupRequest, TokenResponse
from {project}_services import get_auth_service
from {project}_services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, service: AuthService = Depends(get_auth_service)):
    return service.signup(body)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return service.login(body)
```

---

## Empty `__init__.py` files

Create empty `__init__.py` for all package directories not listed above.

---

## After Scaffolding — Tell the User

Once all files are created, tell the user:

```bash
# Install all workspace dependencies
uv sync

# Copy env file and fill in your values
cp .env.example .env

# Start the dev server with hot reload
just dev
```

The API will be at `http://localhost:8000`. Endpoints:
- `GET /healthz` — health check
- `GET /` — root status
- `POST /auth/signup` — create account, returns JWT
- `POST /auth/login` — login, returns JWT

To protect a route, add `user: UserRecord = Depends(get_current_user)` from `{project}_utils`.

To add a dependency to a specific package:
```bash
uv add --package {project}-api <package>   # add to the API app
uv add --package {project}-db <package>    # add to the db package
```

---

## Important Notes

- SQLite is used by default (no external db needed to start). Set `PG_DATABASE_URL` in `.env` to switch to PostgreSQL.
- Tables are auto-created on startup via `Base.metadata.create_all()` — no migrations needed to start.
- The `uv.lock` is at the workspace root — a single lock file covers all packages and apps.
- Docker must be built from the **workspace root** using `just docker-build` (or `docker build -f apps/api/Dockerfile .`).
- To add a new app, create `apps/{name}/` with its own `pyproject.toml` and add it to the workspace root `pyproject.toml` members list.
