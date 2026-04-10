# Chunk 13 — Collaboration API & Messages

## Goal
Implement the full REST API for collaborations: create, list, get details, read messages, cancel, and list sub-runs.

## Depends On
- Chunk 12 (Collaboration Execution Engine)

## Deliverables

### 1. Routes — `api/routes/collaboration.py`

```
POST   /api/v1/collaborations                     → create and start a collaboration
  Body: { agent_ids, title, message, max_rounds?, routing_strategy? }
  Flow:
    1. Validate all agent_ids belong to current org
    2. Create collaboration via CollaborationService
    3. Dispatch execute_group_run.delay(collaboration_id)
    4. Return CollaborationResponse

GET    /api/v1/collaborations                     → list collaborations
  Query: ?status=active&agent_id=...&limit=50

GET    /api/v1/collaborations/{id}                → get collaboration details + members + status

GET    /api/v1/collaborations/{id}/messages       → get the group chat thread
  Query: ?round=3&limit=50
  Returns: list[CollaborationMessageResponse]

POST   /api/v1/collaborations/{id}/cancel         → cancel an active collaboration
  Flow:
    1. Revoke Celery task if running
    2. Cancel any active sub-runs
    3. Set status = "cancelled"

GET    /api/v1/collaborations/{id}/runs           → list all sub-runs
  Returns: list[RunResponse] for all runs with this collaboration_id
```

### 2. Scope Requirements

```
collaborations:read   — list/get collaborations, messages, sub-runs
collaborations:write  — create/cancel collaborations
```

Add these to the scope definitions from Chunk 02.

### 3. Response Enrichment

`GET /collaborations/{id}` returns:
- Collaboration details
- Members list with agent names
- Current status and round
- Resolve summary (if resolved)

`GET /collaborations/{id}/messages` returns:
- Messages with agent names (not just agent_ids)
- Ordered by created_at
- Filterable by round

### 4. Register Router

Add collaboration_router to `api/routes/__init__.py`.

## Notes
- `POST /collaborations` is the entry point for multi-agent work. It creates the data and kicks off execution in one call.
- Messages are read-only via API — only agents can post messages (via the execution engine).
- Cancel revokes the Celery task — any in-progress agent turn may be interrupted.
- Sub-runs are regular Run records with `collaboration_id` set — they show up in both `/runs` and `/collaborations/{id}/runs`.
