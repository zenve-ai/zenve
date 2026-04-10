# Chunk 09 — Agent Runtime Tokens (JWT)

## Goal
Implement short-lived JWT tokens injected into agent processes at execution time, allowing agents to authenticate back to the gateway.

## Depends On
- Chunk 02 (API Key Auth — extends the auth system)
- Chunk 08 (Runs — tokens are scoped to runs)

## Deliverables

### 1. JWT Utility — `utils/jwt.py`

```python
def create_agent_token(
    agent_id: UUID,
    org_id: UUID,
    run_id: UUID,
    scopes: list[str],
    ttl_seconds: int,
) -> str:
    """Create a short-lived JWT for agent runtime auth."""
    payload = {
        "sub": f"agent:{agent_id}",
        "org_id": str(org_id),
        "run_id": str(run_id),
        "scopes": scopes,
        "exp": datetime.utcnow() + timedelta(seconds=ttl_seconds),
        "iat": datetime.utcnow(),
        "type": "agent_runtime",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def verify_agent_token(token: str) -> dict:
    """Verify and decode an agent runtime JWT."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "agent_runtime":
        raise InvalidTokenError("Not an agent runtime token")
    return payload
```

### 2. Config — `config/settings.py`

Add:
```python
JWT_SECRET: str              # required, no default
AGENT_TOKEN_TTL_SECONDS: int = 700  # run timeout + buffer
```

### 3. Default Agent Scopes

```python
DEFAULT_AGENT_SCOPES = [
    "agents:read",       # discover other agents in org
    "runs:read:own",     # read own run status
]
```

### 4. Update RunContext Builder — `services/run_context.py`

Now populate `agent_token`:

```python
def build_run_context(agent, run, message=None):
    token = create_agent_token(
        agent_id=agent.id,
        org_id=agent.org_id,
        run_id=run.id,
        scopes=DEFAULT_AGENT_SCOPES,
        ttl_seconds=settings.AGENT_TOKEN_TTL_SECONDS,
    )
    return RunContext(
        ...
        agent_token=token,
        env_vars={
            "GATEWAY_URL": settings.GATEWAY_URL,
            "GATEWAY_AGENT_TOKEN": token,
            "GATEWAY_AGENT_ID": str(agent.id),
            "GATEWAY_AGENT_SLUG": agent.slug,
            "GATEWAY_ORG_SLUG": agent.organization.slug,
            "GATEWAY_RUN_ID": str(run.id),
        },
    )
```

### 5. Auth Middleware Extension — `api/middleware/auth.py`

Extend `get_current_org` to also accept agent runtime tokens:

```python
async def get_current_auth(authorization: str = Header(...)):
    token = extract_bearer(authorization)

    if token.startswith("gw_live_"):
        # API key auth (existing)
        return authenticate_api_key(token)
    else:
        # JWT auth (agent runtime)
        return authenticate_agent_token(token)
```

Agent tokens return a restricted auth context with limited scopes.

### 6. Scope Enforcement

Agent runtime tokens can only:
- `GET /agents` — list agents in their org
- `GET /agents/{id}` — read agent details
- `GET /runs/{own_run_id}` — read their own run

Any other operation returns 403.

## Notes
- No credentials are stored on disk — tokens are ephemeral and injected via env vars.
- TTL = run timeout + buffer ensures the token is valid for the entire run duration.
- JWT_SECRET must be configured in production (fail if missing).
- Future: expand scopes for agent callbacks (`runs:write:own`, `agents:delegate`).
- The org's master API key is NEVER exposed to agent runtimes.
