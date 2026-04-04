# Implementation Chunks — Overview

Ordered by dependency. Each chunk is self-contained and builds on the previous ones.

| #  | Chunk                          | Depends On | Key Deliverables                                    |
|----|--------------------------------|------------|-----------------------------------------------------|
| 01 | Organizations CRUD             | —          | ORM model, service, routes, Pydantic models         |
| 02 | API Key Auth                   | 01         | API key model, hashing, middleware, scopes           |
| 03 | Agent Filesystem & Templates   | 01         | Template engine, directory scaffolding, gateway.json |
| 04 | Agents CRUD                    | 01, 02, 03 | ORM model, service, routes, file read/write routes   |
| 05 | Adapter Interface              | 04         | BaseAdapter ABC, RunContext, RunResult, registry      |
| 06 | Claude Code Adapter            | 05         | ClaudeCodeAdapter implementation                     |
| 07 | Celery Setup & Run Execution   | 05, 06     | Celery app, Redis broker, execute_agent_run task      |
| 08 | Runs CRUD                      | 07         | ORM model, service, routes, transcript read           |
| 09 | Agent Runtime Tokens (JWT)     | 02, 08     | Short-lived JWT generation, injection, validation     |
| 10 | Heartbeat Scheduler            | 08         | APScheduler, heartbeat_tick, heartbeat routes         |
| 11 | Collaborations Data Model      | 08         | ORM models, service, basic CRUD routes                |
| 12 | Collaboration Execution Engine | 11, 05     | execute_group_run task, routing strategies, RESOLVE   |
| 13 | Collaboration API & Messages   | 12         | Full REST API, message thread, cancel                 |
| 14 | Health & Observability         | 07, 10     | /health, /health/workers, status checks               |
