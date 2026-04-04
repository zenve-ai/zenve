# Chunk 02 — API Key Auth

## Goal
Implement org-scoped API key authentication with scopes. All subsequent routes will require a valid API key.

## Depends On
- Chunk 01 (Organizations)

## Deliverables

### 1. ORM Model — `db/models.py`

Add `ApiKey` table:

```
api_keys
  id              UUID PK
  org_id          UUID FK → organizations
  key_hash        VARCHAR NOT NULL      -- bcrypt hash
  name            VARCHAR NOT NULL      -- human label ("CI key", "dev key")
  scopes          JSON                  -- ["agents:read", "agents:write", "runs:*"]
  is_active       BOOLEAN DEFAULT true
  created_at      TIMESTAMP
  expires_at      TIMESTAMP NULL
```

Relationship: `Organization.api_keys` ↔ `ApiKey.organization`.

### 2. Pydantic Models — `models/api_key.py`

```python
class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["*"]           # default: full access
    expires_at: datetime | None = None

class ApiKeyResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    expires_at: datetime | None

class ApiKeyCreated(ApiKeyResponse):
    raw_key: str                         # shown ONCE at creation
```

### 3. Key Format & Hashing — `utils/api_key.py`

- Generate keys in format: `gw_live_<32-char-random>`
- Hash with bcrypt before storing.
- Lookup: iterate active keys for the matched prefix or use a key prefix index.

### 4. Service — `services/api_key.py`

```python
class ApiKeyService:
    def __init__(self, db: Session): ...
    def create(self, org_id: UUID, data: ApiKeyCreate) -> tuple[ApiKey, str]:
        # Returns (db record, raw_key) — raw_key shown once
    def verify(self, raw_key: str) -> ApiKey | None:
        # Find key by prefix, verify bcrypt hash, check is_active + expiry
    def list_by_org(self, org_id: UUID) -> list[ApiKey]: ...
    def revoke(self, key_id: UUID) -> None: ...
```

### 5. Auth Middleware — `api/middleware/auth.py`

```python
async def get_current_org(
    authorization: str = Header(...),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
) -> tuple[Organization, ApiKey]:
    # Extract Bearer token
    # Verify via api_key_service.verify()
    # Return (org, api_key) — attached to request state
    # Raise 401 if invalid, 403 if expired/inactive
```

Create a `require_scope(scope: str)` dependency for route-level scope checks.

### 6. Update POST /orgs

`POST /orgs` now also creates the first API key and returns it:
```json
{
  "org": { ... },
  "api_key": { "raw_key": "gw_live_...", ... }
}
```

### 7. API Key Routes — `api/routes/api_key.py`

```
GET    /api/v1/api-keys              → list keys for current org
POST   /api/v1/api-keys              → create new key
DELETE /api/v1/api-keys/{key_id}     → revoke key
```

These routes themselves require auth (chicken-and-egg solved by POST /orgs returning the first key).

### 8. Apply Auth to Existing Routes

Add `get_current_org` dependency to all org routes (except POST /orgs which needs a bootstrap path — either unauthenticated or a setup token).

## Scope Definitions

```
agents:read    — list/get agents
agents:write   — create/update/delete agents
runs:read      — list/get runs
runs:write     — trigger/cancel runs
runs:*         — all run operations
*              — full access
```

## Notes
- Raw API key is only returned at creation time. Cannot be recovered.
- Key prefix (`gw_live_`) makes keys easy to identify in logs for rotation.
- Consider a `key_prefix` column (first 8 chars) for faster lookup without iterating all keys.
