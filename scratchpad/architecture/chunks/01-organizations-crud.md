# Chunk 01 — Organizations CRUD

## Goal
Implement the Organization entity end-to-end: ORM model, Pydantic schemas, service layer, and REST routes.

## Depends On
Nothing — this is the foundation.

## Deliverables

### 1. ORM Model — `db/models.py`

Add `Organization` table:

```
organizations
  id              UUID PK (default uuid4)
  name            VARCHAR UNIQUE NOT NULL
  slug            VARCHAR UNIQUE NOT NULL
  base_path       VARCHAR NOT NULL       -- e.g. /data/orgs/acme
  created_at      TIMESTAMP (server_default=now)
  updated_at      TIMESTAMP (onupdate=now)
```

Use `Mapped` / `mapped_column` style per CLAUDE.md rules.

### 2. Pydantic Models — `models/org.py`

```python
class OrgCreate(BaseModel):
    name: str               # "Acme Corp"
    slug: str | None = None # auto-generated from name if not provided

class OrgUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None

class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    base_path: str
    created_at: datetime
    updated_at: datetime
```

### 3. Service — `services/org.py`

```python
class OrgService:
    def __init__(self, db: Session): ...
    def create(self, data: OrgCreate) -> Organization: ...
    def get_by_id(self, org_id: UUID) -> Organization: ...
    def get_by_slug(self, slug: str) -> Organization: ...
    def list_all(self) -> list[Organization]: ...
    def update(self, org_id: UUID, data: OrgUpdate) -> Organization: ...
```

- Auto-generate `slug` from `name` (slugify) if not provided.
- Auto-generate `base_path` as `{settings.data_dir}/orgs/{slug}`.
- Create the org directory on disk at creation time.

### 4. Dependency Function — `services/__init__.py`

```python
def get_org_service(db: Session = Depends(get_db)) -> OrgService:
    return OrgService(db)
```

### 5. Routes — `api/routes/org.py`

```
POST   /api/v1/orgs           → create org (returns OrgResponse)
GET    /api/v1/orgs           → list orgs
GET    /api/v1/orgs/{org_id}  → get org by UUID or slug
PATCH  /api/v1/orgs/{org_id}  → update org
```

Thin wrappers only — delegate everything to OrgService via Depends.

### 6. Register Router — `api/routes/__init__.py` + `main.py`

Add org_router to the app.

## Config

Add `DATA_DIR` to settings (default: `/data` or configurable via env var).

## Notes
- No auth on these routes yet (added in Chunk 02).
- `POST /orgs` will later also return the first API key (Chunk 02).
- Soft validation: slug must be lowercase alphanumeric + hyphens.
