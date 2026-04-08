"""TDD tests for the run event system additions to ClaudeCodeAdapter.

These tests define expected behaviour for Chunk 15 (15-run-event-system.md).
All tests intentionally FAIL until the implementation is complete:

  - RunContext gains an `on_event: OnEventCallback` field
  - ClaudeCodeAdapter.execute() switches to --output-format stream-json
  - Each stream-json line is parsed and translated to an on_event() call
  - ClaudeCodeConfig.output_format defaults to "stream-json"

Responsibility split (from the spec):
  - Celery task emits: started, completed, failed, timeout
  - Adapter emits:     output, tool_call, tool_result, error, usage
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_models.adapter import ClaudeCodeConfig, RunContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(on_event=None) -> RunContext:
    """Build a minimal RunContext with an injectable on_event callback."""
    return RunContext(
        agent_dir="/tmp/fake-agent",
        agent_id="agent-1",
        agent_slug="my-agent",
        agent_name="My Agent",
        org_id="org-1",
        org_slug="my-org",
        run_id="run-1",
        adapter_type="claude_code",
        adapter_config={},
        message="do something",
        heartbeat=False,
        gateway_url="http://gateway",
        agent_token="tok",
        on_event=on_event if on_event is not None else (lambda *a, **kw: None),
    )


class _AsyncLineIter:
    """Async iterator over a list of raw bytes lines (simulates proc.stdout)."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration


def _make_proc(
    lines: list[bytes],
    stderr: bytes = b"",
    returncode: int = 0,
) -> MagicMock:
    """Return a mock asyncio subprocess whose stdout yields *lines*."""
    proc = MagicMock()
    proc.stdout = _AsyncLineIter(lines)
    proc.returncode = returncode
    proc.wait = AsyncMock(return_value=None)

    stderr_stream = MagicMock()
    stderr_stream.read = AsyncMock(return_value=stderr)
    proc.stderr = stderr_stream

    return proc


def _json_line(payload: dict) -> bytes:
    return (json.dumps(payload) + "\n").encode()


# ---------------------------------------------------------------------------
# A. Config defaults
# ---------------------------------------------------------------------------


def test_claude_code_config_default_output_format_is_stream_json():
    """ClaudeCodeConfig must default to stream-json, not json."""
    config = ClaudeCodeConfig()
    assert config.output_format == "stream-json"


def test_build_cli_args_passes_stream_json():
    """_build_cli_args must pass --output-format stream-json to the CLI."""
    adapter = ClaudeCodeAdapter()
    config = ClaudeCodeConfig(output_format="stream-json")

    args = adapter._build_cli_args(config, "hello", "sys-prompt", tools=None)

    assert "--output-format" in args
    idx = args.index("--output-format")
    assert args[idx + 1] == "stream-json"


# ---------------------------------------------------------------------------
# B. System event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_system_event_emits_output_with_session_id():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({"type": "system", "session_id": "sess_abc123"})

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=_make_proc([line]),
        ),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "output"
    assert "sess_abc123" in kwargs.get("content", "")
    assert kwargs.get("metadata", {}).get("session_id") == "sess_abc123"


@pytest.mark.asyncio
async def test_system_event_missing_session_id_uses_unknown():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({"type": "system"})

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "output"
    assert "unknown" in kwargs.get("content", "").lower()


# ---------------------------------------------------------------------------
# C. Assistant event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assistant_event_emits_output_with_text():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({
        "type": "assistant",
        "message": {"content": "I found 3 issues."},
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "output"
    assert kwargs["content"] == "I found 3 issues."


@pytest.mark.asyncio
async def test_assistant_event_with_list_content_joins_text_blocks():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "Hello "},
                {"type": "text", "text": "world"},
            ]
        },
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "output"
    assert kwargs["content"] == "Hello world"


@pytest.mark.asyncio
async def test_assistant_event_empty_text_is_not_emitted():
    """An assistant event with no textual content must not call on_event."""
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({
        "type": "assistant",
        "message": {"content": ""},
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert events == []


# ---------------------------------------------------------------------------
# D. Tool-call event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_use_event_emits_tool_call():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({
        "type": "tool_use",
        "name": "Read",
        "id": "tu_abc",
        "input": {"path": "src/auth.py"},
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "tool_call"
    assert "Read" in kwargs.get("content", "")
    meta = kwargs.get("metadata", {})
    assert meta["tool"] == "Read"
    assert meta["tool_use_id"] == "tu_abc"
    assert meta["input"] == {"path": "src/auth.py"}


# ---------------------------------------------------------------------------
# E. Tool-result event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_result_event_emits_tool_result():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({
        "type": "tool_result",
        "tool_use_id": "tu_abc",
        "content": "def authenticate(): ...",
        "is_error": False,
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "tool_result"
    meta = kwargs.get("metadata", {})
    assert meta["tool_use_id"] == "tu_abc"
    assert meta["is_error"] is False
    assert "def authenticate" in kwargs.get("content", "")


@pytest.mark.asyncio
async def test_tool_result_content_truncated_at_500_chars():
    """Content in on_event() must be capped at 500 chars; full result in metadata."""
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    long_content = "x" * 1000

    line = _json_line({
        "type": "tool_result",
        "tool_use_id": "tu_xyz",
        "content": long_content,
        "is_error": False,
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    (_, kwargs) = events[0][0], events[0][1]
    # content field must be ≤ 503 chars (500 + "...")
    assert len(kwargs["content"]) <= 503
    assert kwargs["content"].endswith("...")
    # full result preserved in metadata
    assert kwargs["metadata"]["full_result"] == long_content


# ---------------------------------------------------------------------------
# F. Result (usage) event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_event_emits_usage_with_token_counts():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({
        "type": "result",
        "total_cost_usd": 0.012,
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 340,
            "cache_read_input_tokens": 50,
            "cache_creation_input_tokens": 10,
        },
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "usage"
    meta = kwargs.get("metadata", {})
    assert meta["input_tokens"] == 1200
    assert meta["output_tokens"] == 340
    assert meta["cache_read_input_tokens"] == 50
    assert meta["cache_creation_input_tokens"] == 10
    assert meta["cost_usd"] == 0.012


@pytest.mark.asyncio
async def test_result_event_without_usage_block_does_not_emit():
    """A result line with no usage dict must not call on_event."""
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({"type": "result", "subtype": "success"})

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert events == []


# ---------------------------------------------------------------------------
# G. Error event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_event_emits_error_with_message():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({
        "type": "error",
        "message": "tool execution failed",
    })

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "error"
    assert kwargs["content"] == "tool execution failed"
    assert kwargs["metadata"]["type"] == "error"


@pytest.mark.asyncio
async def test_error_event_missing_message_uses_fallback():
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({"type": "error"})

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "error"
    assert kwargs["content"]  # non-empty fallback


# ---------------------------------------------------------------------------
# H. Non-JSON and unknown types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_json_line_emits_output():
    """A line that is not valid JSON must be forwarded as an output event."""
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = b"some plain text from stderr redirect\n"

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert len(events) == 1
    (event_type,), kwargs = events[0]
    assert event_type == "output"
    assert "some plain text" in kwargs["content"]


@pytest.mark.asyncio
async def test_blank_lines_are_skipped():
    """Blank / whitespace-only lines must not generate any events."""
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([b"\n", b"   \n", b""])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert events == []


@pytest.mark.asyncio
async def test_unknown_event_type_is_silently_ignored():
    """Future/unknown Claude Code event types must not call on_event (forward compat)."""
    events: list[tuple] = []
    ctx = _make_ctx(on_event=lambda *a, **kw: events.append((a, kw)))

    line = _json_line({"type": "new_future_type", "data": "irrelevant"})

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([line])),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert events == []


# ---------------------------------------------------------------------------
# I. RunResult correctness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_correct_exit_code_on_success():
    ctx = _make_ctx()

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc([], returncode=0)),
    ):
        result = await ClaudeCodeAdapter().execute(ctx)

    assert result.exit_code == 0
    assert result.error is None


@pytest.mark.asyncio
async def test_execute_returns_nonzero_exit_code_on_failure():
    ctx = _make_ctx()
    stderr_msg = b"claude crashed"

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch(
            "asyncio.create_subprocess_exec",
            return_value=_make_proc([], stderr=stderr_msg, returncode=1),
        ),
    ):
        result = await ClaudeCodeAdapter().execute(ctx)

    assert result.exit_code == 1
    assert result.error == "claude crashed"


@pytest.mark.asyncio
async def test_execute_token_usage_populated_from_result_event():
    """RunResult.token_usage must be set from the stream-json result line."""
    ctx = _make_ctx()

    lines = [
        _json_line({
            "type": "result",
            "total_cost_usd": 0.005,
            "usage": {"input_tokens": 100, "output_tokens": 50},
        })
    ]

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc(lines)),
    ):
        result = await ClaudeCodeAdapter().execute(ctx)

    assert result.token_usage is not None
    assert result.token_usage["input_tokens"] == 100
    assert result.token_usage["output_tokens"] == 50
    assert result.token_usage["cost_usd"] == 0.005


@pytest.mark.asyncio
async def test_execute_stdout_accumulates_all_raw_lines():
    """RunResult.stdout must contain every raw line joined by newlines."""
    ctx = _make_ctx()

    lines = [
        _json_line({"type": "system", "session_id": "s1"}),
        _json_line({"type": "assistant", "message": {"content": "hi"}}),
    ]

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc(lines)),
    ):
        result = await ClaudeCodeAdapter().execute(ctx)

    assert "session_id" in result.stdout
    assert "assistant" in result.stdout


# ---------------------------------------------------------------------------
# J. Event ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_events_emitted_in_stream_order():
    """on_event must be called in the same order the lines arrive from stdout."""
    order: list[str] = []

    def record_event(event_type: str, content=None, metadata=None):
        order.append(event_type)

    ctx = _make_ctx(on_event=record_event)

    lines = [
        _json_line({"type": "system", "session_id": "s1"}),
        _json_line({"type": "assistant", "message": {"content": "thinking..."}}),
        _json_line({"type": "tool_use", "name": "Bash", "id": "t1", "input": {}}),
        _json_line({"type": "tool_result", "tool_use_id": "t1", "content": "ok", "is_error": False}),
        _json_line({
            "type": "result",
            "total_cost_usd": 0.001,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }),
    ]

    with (
        patch("zenve_adapters.claude_code.ClaudeCodeAdapter._read_file", return_value=""),
        patch("asyncio.create_subprocess_exec", return_value=_make_proc(lines)),
    ):
        await ClaudeCodeAdapter().execute(ctx)

    assert order == ["output", "output", "tool_call", "tool_result", "usage"]
