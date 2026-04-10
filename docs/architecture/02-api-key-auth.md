# Chunk 02 — API Key Auth

## Goal
Provide org-scoped API key authentication with granular scopes. Every API route (except org creation bootstrap) requires a valid API key. This replaces the existing user-level JWT auth (`utils/auth.py`, `services/auth.py`, `api/routes/auth.py`) for gateway access — those files will be removed or repurposed once this feature is complete.

## Depends On
- Chunk 01 — Organizations (provides `Organization` ORM model and `OrgService`)

## Referenced By
- Chunk 04 — Agents CRUD (routes require API key auth)
- Chunk 08 — Runs CRUD (routes require API key auth)
- Chunk 09 — Agent Runtime Tokens (JWT minted from API key context)

## Deliverables

### 1. ORM Model — `db/models.py`

Add `ApiKeyRecord` table alongside existing `Organization`:

```python
class ApiKeyRecord(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(nullable=False)          # bcrypt hash
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # first 12 chars for lookup
    name: Mapped[str] = mapped_column(nullable=False)              # human label ("CI key", "dev key")
    scopes: Mapped[str] = mapped_column(default="*")               # comma-separated: "agents:read,runs:*"
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="api_keys")
```

Add to `Organization`:
```python
api_keys: Mapped[list["ApiKeyRecord"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
```

**Design note**: `scopes` stored as comma-separated string (not JSON) for SQLite compatibility. Parsed to `list[str]` in the Pydantic layer.

**Design note**: `key_prefix` stores the first 12 characters of the raw key (e.g., `zv_live_abcd`) for O(1) lookup — avoids iterating all keys and bcrypt-comparing each one.

### 2. Pydantic Models — `models/api_key.py`

```python
class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["*"]           # default: full access
    expires_at: datetime | None = None

class ApiKeyResponse(BaseModel):
    id: str
    org_id: str
    name: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}

    @field_validator("scopes", mode="before")
    @classmethod
    def parse_scopes(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

class ApiKeyCreated(ApiKeyResponse):
    raw_key: str                         # shown ONCE at creation time
```

### 3. Key Format & Hashing — `utils/api_key.py`

```python
import secrets
import bcrypt

PREFIX = "zv_live_"

def generate_api_key() -> str:
    """Generate a raw API key: zv_live_<32-char-hex>."""
    return PREFIX + secrets.token_hex(16)

def hash_api_key(raw_key: str) -> str:
    """Bcrypt-hash the raw key for storage."""
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()

def verify_api_key(raw_key: str, key_hash: str) -> bool:
    """Verify a raw key against its bcrypt hash."""
    return bcrypt.checkpw(raw_key.encode(), key_hash.encode())

def extract_prefix(raw_key: str) -> str:
    """Extract the lookup prefix (first 12 chars) from a raw key."""
    return raw_key[:12]
```

Key format: `zv_live_<32-hex-chars>` (total 40 chars). Prefix `zv_live_` identifies zenve keys in logs and credential scanners.

### 4. Service — `services/api_key.py`

```python
class ApiKeyService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, org_id: str, data: ApiKeyCreate) -> tuple[ApiKeyRecord, str]:
        """Create a new API key. Returns (record, raw_key). Raw key shown once."""

    def verify(self, raw_key: str) -> ApiKeyRecord | None:
        """Look up by prefix, verify bcrypt hash, check is_active + expiry.
        Returns None if invalid/expired/inactive."""

    def list_by_org(self, org_id: str) -> list[ApiKeyRecord]:
        """List all keys for an org (active and inactive)."""

    def revoke(self, key_id: str) -> ApiKeyRecord:
        """Set is_active=False. Raises 404 if not found."""
```

Lookup flow: `key_prefix` column indexed for fast DB query -> single bcrypt verify on the matched row.

### 5. Dependency Function — `services/__init__.py`

```python
def get_api_key_service(db: Session = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(db)
```

### 6. Auth Dependency — `utils/api_key_auth.py`

```python
async def get_current_org(
    authorization: str = Header(..., alias="Authorization"),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
    org_service: OrgService = Depends(get_org_service),
) -> tuple[Organization, ApiKeyRecord]:
    """Extract Bearer token, verify API key, return (org, key).
    Raises 401 if missing/invalid, 403 if expired/inactive."""

def require_scope(scope: str) -> Callable:
    """Returns a dependency that checks if the current API key has the given scope.
    Scope matching: 'agents:read' matches 'agents:read', 'agents:*', or '*'.
    Raises 403 if scope not granted."""
```

**Placement**: This lives in `utils/` (not `api/middleware/`) because it's a FastAPI dependency function, not ASGI middleware. Same pattern as existing `utils/auth.py`.

### 7. Routes — `api/routes/api_key.py`

| Method | Path                          | Auth Required | Description                    |
|--------|-------------------------------|---------------|--------------------------------|
| POST   | `/api/v1/api-keys`            | Yes           | Create new key for current org |
| GET    | `/api/v1/api-keys`            | Yes           | List keys for current org      |
| DELETE | `/api/v1/api-keys/{key_id}`   | Yes           | Revoke a key                   |

### 8. Bootstrap: Update `POST /api/v1/orgs`

`POST /api/v1/orgs` remains **unauthenticated** (or protected by a setup token from `settings.setup_token`). On org creation, it auto-generates the first API key and returns it:

```python
class OrgCreatedResponse(BaseModel):
    org: OrgResponse
    api_key: ApiKeyCreated
```

This solves the chicken-and-egg problem: you need an API key to call the API, but you need to call the API to create an API key.

### 9. Apply Auth to Existing Routes

All existing routes gain the `get_current_org` dependency:
- `GET /api/v1/orgs` — requires valid key, returns only the key's org
- `GET /api/v1/orgs/{org_id}` — requires valid key, must match key's org
- `PATCH /api/v1/orgs/{org_id}` — requires valid key + scope check

`POST /api/v1/orgs` remains open (bootstrap).

## Scope Definitions

```
agents:read    — list/get agents
agents:write   — create/update/delete agents
runs:read      — list/get runs
runs:write     — trigger/cancel runs
runs:*         — all run operations
keys:read      — list API keys
keys:write     — create/revoke API keys
*              — full access (default for first key)
```

Scope matching rules:
- Exact match: `agents:read` grants `agents:read`
- Wildcard domain: `agents:*` grants `agents:read` and `agents:write`
- Full wildcard: `*` grants everything

## Config

| Variable | Setting Field | Default | Purpose |
|----------|--------------|---------|---------|
| `SETUP_TOKEN` | `settings.setup_token` | `None` | Optional token to protect `POST /orgs` bootstrap endpoint |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Key prefix for lookup | Store first 12 chars in `key_prefix` column | Avoids scanning all keys + bcrypt on each. O(1) lookup. |
| Scopes as comma-separated string | `"agents:read,runs:*"` not JSON | SQLite has no native JSON column. Simple parse in Pydantic. |
| Key format | `zv_live_<32-hex>` | Identifiable in logs, rotatable. `zv_` = zenve. |
| Auth as dependency, not middleware | `Depends(get_current_org)` per route | Explicit, testable, allows per-route opt-out (bootstrap). |
| Bootstrap via POST /orgs | Returns first API key with org | No separate setup flow. One call to start. |
| Existing JWT auth | Kept for now, separate concern | User auth (`UserRecord`) may coexist or be removed later. API key auth is for programmatic gateway access. |

## Notes

- Raw API key is returned only at creation time. Cannot be recovered — must revoke and create a new one.
- `key_prefix` must be indexed in the DB for fast lookups.
- The existing `UserRecord` / JWT auth system in `utils/auth.py` is a separate concern (user login). It may be removed if the gateway is purely API-key-authenticated, but that decision is deferred.
- `bcrypt` is already a project dependency (used in `utils/auth.py`).

## Implementation Status
- **Status**: not started

## Change Log
| Date | Change | Reason |
|------|--------|--------|
| 2026-04-05 | Initial architecture draft | Documented planned feature |
| 2026-04-05 | Revised: fixed status to not-started, refined design for actual codebase | Status was incorrectly marked as implemented. Redesigned key lookup (key_prefix column), scopes storage (comma-separated for SQLite), auth placement (utils/ not middleware/), and bootstrap flow based on actual code review. |
