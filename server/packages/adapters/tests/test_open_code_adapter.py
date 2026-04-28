from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from zenve_adapters.open_code import OpenCodeAdapter
from zenve_models.adapter import OpenCodeConfig, RunContext
from zenve_utils.testing import json_line, make_proc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_ctx(on_event=None, **kwargs) -> RunContext:
    """Minimal RunContext for execute() tests."""
    defaults = dict(
        agent_dir="/tmp",
        project_dir="/tmp",
        agent_id="a1",
        agent_slug="dev",
        agent_name="Dev",
        project_slug="acme",
        run_id="r1",
        adapter_type="open_code",
        adapter_config={},
        message="hello",
        heartbeat=False,
    )
    defaults.update(kwargs)
    if on_event is not None:
        defaults["on_event"] = on_event
    return RunContext(**defaults)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


def test_build_cli_args_defaults():
    adapter = OpenCodeAdapter()
    config = OpenCodeConfig()

    args = adapter.build_cli_args(config)

    assert args == ["opencode", "run", "--format", "json"]
    assert "--model" not in args


def test_build_cli_args_custom_model():
    adapter = OpenCodeAdapter()
    config = OpenCodeConfig(model="openai/gpt-4o")

    args = adapter.build_cli_args(config)

    assert "--model" in args
    assert "openai/gpt-4o" in args



# ---------------------------------------------------------------------------
# on_event tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_event_session_id():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "text", "sessionID": "sess-abc", "part": {"text": "Hi"}}),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    assert events[0] == ("output", "Session started: sess-abc", {"session_id": "sess-abc"})
    assert events[1] == ("output", "Hi", None)


@pytest.mark.asyncio
async def test_on_event_text():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "text", "part": {"text": "Hello from OpenCode!"}}),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    assert events == [("output", "Hello from OpenCode!", None)]


@pytest.mark.asyncio
async def test_on_event_tool_use():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {
                    "type": "tool_use",
                    "part": {
                        "name": "Glob",
                        "input": {"pattern": "*.py"},
                        "state": {"status": "running"},
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    assert len(events) == 1
    event_type, content, meta = events[0]
    assert event_type == "tool_call"
    assert content == "Calling tool: Glob"
    assert meta == {"tool": "Glob", "input": {"pattern": "*.py"}}


@pytest.mark.asyncio
async def test_on_event_tool_use_error():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {
                    "type": "tool_use",
                    "part": {
                        "name": "Bash",
                        "input": {"command": "rm -rf /"},
                        "state": {"status": "error", "error": "permission denied"},
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    assert len(events) == 1
    event_type, content, meta = events[0]
    assert event_type == "tool_call"
    assert content == "Tool error: Bash: permission denied"
    assert meta["tool"] == "Bash"
    assert meta["error"] == "permission denied"


@pytest.mark.asyncio
async def test_on_event_step_finish():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {
                    "type": "step_finish",
                    "part": {
                        "tokens": {
                            "input": 100,
                            "output": 50,
                            "reasoning": 10,
                            "cache": {"read": 20},
                        },
                        "cost": 0.05,
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    assert len(events) == 1
    event_type, content, meta = events[0]
    assert event_type == "usage"
    assert content is None
    assert meta == {
        "input_tokens": 100,
        "output_tokens": 50,
        "reasoning_tokens": 10,
        "cache_read_input_tokens": 20,
        "cost_usd": 0.05,
    }


@pytest.mark.asyncio
async def test_on_event_error():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "error", "error": "rate limit exceeded"}),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    assert events == [("error", "rate limit exceeded", {"type": "error"})]


@pytest.mark.asyncio
async def test_on_event_error_nested():
    """Error event with a dict error value extracts the message field."""
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "error", "error": {"message": "model unavailable"}}),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    assert events == [("error", "model unavailable", {"type": "error"})]


@pytest.mark.asyncio
async def test_on_event_full_sequence():
    """Smoke test: all event types fire in the right order."""
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "text", "sessionID": "s1", "part": {"text": "Thinking..."}}),
            json_line(
                {
                    "type": "tool_use",
                    "part": {
                        "name": "Glob",
                        "input": {},
                        "state": {"status": "running"},
                    },
                }
            ),
            json_line({"type": "text", "part": {"text": "Done."}}),
            json_line(
                {
                    "type": "step_finish",
                    "part": {
                        "tokens": {
                            "input": 10,
                            "output": 5,
                            "reasoning": 0,
                            "cache": {"read": 0},
                        },
                        "cost": 0.01,
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await OpenCodeAdapter().execute(ctx)

    types = [e[0] for e in events]
    assert types == ["output", "output", "tool_call", "output", "usage"]
