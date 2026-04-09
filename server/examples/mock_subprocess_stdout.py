"""
How subprocess mocking relates to the Claude adapter and tests.

**Today’s `ClaudeCodeAdapter.execute()`** (`zenve_adapters/claude_code.py`) uses:

    proc = await asyncio.create_subprocess_exec(..., stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout_bytes, stderr_bytes = await proc.communicate(input=message.encode())

So the real code never does `async for line in proc.stdout`. It sends the whole
message on stdin once, waits for the process to finish, then gets **two byte
blobs** — full stdout and full stderr.

**`make_proc` in `zenve_utils.testing`** is built for **tests that expect a
streaming reader**: `stdout` is an async iterator that yields **lines** (like
stream-json). That matches the *intended* event-system behavior described in
`test_event_system.py`, not the current `communicate()` implementation.

This file shows both patterns side by side so the distinction is obvious.

Usage:
    uv run python examples/mock_subprocess_stdout.py
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from zenve_utils.testing import make_proc

# --- 1) Same *shape* as today’s adapter: communicate() ---------------------------------


async def like_current_adapter_execute() -> None:
    """Mimic `execute()`: one stdin write, then full stdout/stderr bytes."""
    fake_stdout = b'{"usage":{"input_tokens":1,"output_tokens":2}}\n'
    fake_stderr = b""

    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(fake_stdout, fake_stderr))
    proc.returncode = 0

    message = b"user message on stdin"
    stdout_bytes, stderr_bytes = await proc.communicate(input=message)

    print("--- Pattern: communicate() (matches current claude_code.execute) ---")
    print(f"  wrote to stdin (conceptually): {len(message)} bytes")
    print(f"  stdout (full): {stdout_bytes!r}")
    print(f"  stderr (full): {stderr_bytes!r}")
    print()


# --- 2) What `make_proc` is for: async line iteration (tests / streaming) -------------


async def like_event_system_tests() -> None:
    """Mimic tests: read stdout as an async stream of lines (not communicate())."""
    fake_lines = [
        b'{"type":"system","session_id":"sess_demo"}\n',
        b'{"type":"assistant","message":{"content":"Hello"}}\n',
    ]

    proc = make_proc(fake_lines)

    lines: list[bytes] = []
    async for line in proc.stdout:
        lines.append(line)
    await proc.wait()

    print("--- Pattern: async for line in proc.stdout (make_proc / event tests) ---")
    for i, raw in enumerate(lines, start=1):
        print(f"  line {i}: {raw!r}")
    print()
    print(
        "  This is *not* what execute() does today; it is what the mock supports "
        "so streaming JSON lines can be tested without the real CLI."
    )


async def main() -> None:
    await like_current_adapter_execute()
    await like_event_system_tests()


if __name__ == "__main__":
    asyncio.run(main())
