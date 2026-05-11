# TODO

## [ ] SSE Streaming of live run events

The runtime's `run_trigger_service.py` `on_event` callback only logs events.
Add a `GET /workspaces/{id}/runs/{run_id}/stream` SSE endpoint so clients can
subscribe to live event updates while a run is in progress.

## [ ] CLI `zenve run` delegates to runtime via HTTP

`commands/run.py` currently calls `ensure_runtime()` then executes the engine
locally and launches the TUI with a local `run_fn`. It should instead call
`POST /workspaces/{id}/runs` and consume the SSE stream from the runtime.
Requires SSE streaming to be done first.

## [ ] Scheduling moved from TUI into runtime daemon

The cron loop lives in `console/tui.py` (`execute_run`, croniter, sleep,
`run_now_event`). Move schedule ownership into the runtime daemon — store each
workspace's `run_schedule` and fire runs there. The CLI `status` command should
only read schedule state from the runtime, not drive it.
