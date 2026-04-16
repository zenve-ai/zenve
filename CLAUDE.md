# CLAUDE.md

Zenve monorepo root.

## Structure

```
server/   # FastAPI backend (see server/CLAUDE.md)
ui/       # Frontend (see ui/CLAUDE.md)
agents/   # Agent definitions
```

## Auth Model

- **JWT auth** — user login/signup, used for org CRUD (`/api/v1/orgs`)
- **API key auth** — programmatic access, used for agent/api-key routes
- **User–Org membership** — `Membership` table with roles (`owner`, `admin`, `member`)
- See [server/CLAUDE.md](server/CLAUDE.md) for full auth details

## Sub-project docs

- [server/CLAUDE.md](server/CLAUDE.md) — FastAPI monorepo: architecture rules, auth model, layer rules, dev commands
- [ui/CLAUDE.md](ui/CLAUDE.md) — React SPA: stack, structure, Redux/RTK Query, routing, component rules
