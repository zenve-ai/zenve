# API Refactor 05 — Webhook Receiver + WebSocket Broadcast

## Goal

Add a webhook endpoint that receives CLI run events (HMAC-verified) and broadcasts them to WebSocket clients. No persistence — historical events come from committed `runs/{id}.json`.

## New route (`apps/api/src/api/routes/webhook.py`)

### `POST /api/v1/webhooks/zenve-events`
- Verify `X-Zenve-Signature` header (HMAC-SHA256 with `zenve_webhook_secret`)
- Read `X-Zenve-Project-Id` header to scope broadcast
- Push JSON body to connected WS clients for that project
- No DB writes

### `POST /api/v1/webhooks/github`
- Behind `github_webhook_secret` if set
- Handle `installation` / `installation_repositories` events
- Auto-disconnect projects whose installation was uninstalled

## Refactor: WS manager (`packages/services/src/zenve_services/ws_manager.py`)
Trim to three methods:
- `connect(project_id, ws)`
- `disconnect(ws)`
- `broadcast(project_id, event)`
- Remove all run-lifecycle coupling

## Update: WS route (`apps/api/src/api/routes/ws.py`)
- Key subscriptions by `project_id` (was `org_id`)
- JWT-auth unchanged

## CLI coordination (out of scope but noted)
- CLI must add `X-Zenve-Project-Id` header to webhook posts
- CLI payload: `{run_id, timestamp, type, agent, data}`

## Dependencies
- Requires plan 01 (project_id)
- Requires plan 03 (HMAC verification util, webhook secrets config)

## Verification
1. Open WS subscribed to `project_id`
2. `curl` webhook endpoint with valid HMAC + `X-Zenve-Project-Id` + event body → WS client receives broadcast
3. Tamper the HMAC → 401, no broadcast
4. No DB rows written for events
