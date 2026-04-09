from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_models.adapter import ClaudeCodeConfig, RunContext
from zenve_utils.testing import json_line, make_proc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_ctx(on_event=None, **kwargs) -> RunContext:
    """Minimal RunContext for execute() tests."""
    defaults = dict(
        agent_dir="/tmp",
        agent_id="a1",
        agent_slug="dev",
        agent_name="Dev",
        org_id="o1",
        org_slug="acme",
        run_id="r1",
        adapter_type="claude_code",
        adapter_config={},
        message="hello",
        heartbeat=False,
        gateway_url="http://localhost:8000",
        agent_token="",
    )
    defaults.update(kwargs)
    if on_event is not None:
        defaults["on_event"] = on_event
    return RunContext(**defaults)


def test_parse_token_usage_usage_key():
    adapter = ClaudeCodeAdapter()
    stdout = '{"usage": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.005}}'

    result = adapter.parse_token_usage(stdout)

    assert result == {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.005}


def test_parse_token_usage_invalid_json_returns_none():
    adapter = ClaudeCodeAdapter()

    assert adapter.parse_token_usage("not json at all") is None
    assert adapter.parse_token_usage("") is None


def test_build_cli_args_with_tools():
    adapter = ClaudeCodeAdapter()
    config = ClaudeCodeConfig(model="claude-sonnet-4-6", max_turns=5)

    args = adapter.build_cli_args(config, "hello", "system prompt", tools=["Bash", "Read"])

    assert "--allowedTools" in args
    assert "Bash,Read" in args
    assert "--dangerously-skip-permissions" not in args


def test_build_cli_args_no_tools_skips_permissions():
    adapter = ClaudeCodeAdapter()
    config = ClaudeCodeConfig()

    args = adapter.build_cli_args(config, "hello", "system prompt", tools=None)

    assert "--dangerously-skip-permissions" in args
    assert "--allowedTools" not in args


# ---------------------------------------------------------------------------
# on_event tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_event_system():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "system", "session_id": "sess-abc"}),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    assert events == [("output", "Session started: sess-abc", {"session_id": "sess-abc"})]


@pytest.mark.asyncio
async def test_on_event_assistant_text():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello!"}]}}
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    assert events == [("output", "Hello!", None)]


@pytest.mark.asyncio
async def test_on_event_assistant_tool_use():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Glob",
                                "id": "tu_1",
                                "input": {"pattern": "*.py"},
                            },
                        ]
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    event_type, content, meta = events[0]
    assert event_type == "tool_call"
    assert content == "Calling tool: Glob"
    assert meta == {"tool": "Glob", "tool_use_id": "tu_1", "input": {"pattern": "*.py"}}


@pytest.mark.asyncio
async def test_on_event_assistant_mixed_blocks():
    """Text block followed by tool_use block both fire separate events."""
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "Let me check."},
                            {
                                "type": "tool_use",
                                "name": "Read",
                                "id": "tu_2",
                                "input": {"path": "foo.py"},
                            },
                        ]
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    assert events[0] == ("output", "Let me check.", None)
    assert events[1][0] == "tool_call"
    assert events[1][1] == "Calling tool: Read"


@pytest.mark.asyncio
async def test_on_event_user_tool_result():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "tu_1",
                                "content": "file contents",
                                "is_error": False,
                            },
                        ]
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    event_type, content, meta = events[0]
    assert event_type == "tool_result"
    assert content == "file contents"
    assert meta["tool_use_id"] == "tu_1"
    assert meta["is_error"] is False
    assert meta["full_result"] == "file contents"


@pytest.mark.asyncio
async def test_on_event_tool_result_truncated():
    """Results longer than 500 chars are truncated with '...' in the emitted content."""
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    long_content = "x" * 600
    proc = make_proc(
        [
            json_line(
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "tu_2",
                                "content": long_content,
                                "is_error": False,
                            },
                        ]
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    _, content, meta = events[0]
    assert content == long_content[:500] + "..."
    assert meta["full_result"] == long_content


@pytest.mark.asyncio
async def test_on_event_result_usage():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line(
                {
                    "type": "result",
                    "total_cost_usd": 0.05,
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_read_input_tokens": 10,
                        "cache_creation_input_tokens": 5,
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    event_type, content, meta = events[0]
    assert event_type == "usage"
    assert content is None
    assert meta == {
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_input_tokens": 10,
        "cache_creation_input_tokens": 5,
        "cost_usd": 0.05,
    }


@pytest.mark.asyncio
async def test_on_event_error():
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "error", "message": "rate limit exceeded"}),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    assert events == [("error", "rate limit exceeded", {"type": "error"})]


@pytest.mark.asyncio
async def test_on_event_full_sequence():
    """Smoke test: all event types fire in the right order."""
    events: list[tuple] = []
    ctx = make_ctx(on_event=lambda *a: events.append(a))

    proc = make_proc(
        [
            json_line({"type": "system", "session_id": "s1"}),
            json_line(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "tool_use", "name": "Glob", "id": "t1", "input": {}},
                        ]
                    },
                }
            ),
            json_line(
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "t1",
                                "content": "found.py",
                                "is_error": False,
                            },
                        ]
                    },
                }
            ),
            json_line(
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}}
            ),
            json_line(
                {
                    "type": "result",
                    "total_cost_usd": 0.01,
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                    },
                }
            ),
        ]
    )
    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        await ClaudeCodeAdapter().execute(ctx)

    types = [e[0] for e in events]
    assert types == ["output", "tool_call", "tool_result", "output", "usage"]
