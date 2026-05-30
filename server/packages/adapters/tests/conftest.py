from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock


def json_line(obj: dict) -> bytes:
    """Encode a dict as a newline-terminated JSON bytes line."""
    return (json.dumps(obj) + "\n").encode()


class _AsyncLineIter:
    """Async stdout stub supporting both `async for` and `readline()`.

    Yields pre-loaded byte lines; `readline()` returns b"" at EOF, matching
    asyncio.StreamReader (the adapters read via `await proc.stdout.readline()`).
    """

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self._lines)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def readline(self) -> bytes:
        return next(self._lines, b"")


def make_proc(lines: list[bytes]) -> MagicMock:
    """Build a mock asyncio subprocess whose stdout async-iterates the given lines."""
    proc = MagicMock()
    proc.returncode = 0

    # stdin: write() is sync, drain()/close() are sync/async mix
    stdin = MagicMock()
    stdin.drain = AsyncMock()
    proc.stdin = stdin

    # stdout: supports async for
    proc.stdout = _AsyncLineIter(lines)

    # stderr: must be awaitable via .read()
    stderr = AsyncMock()
    stderr.read = AsyncMock(return_value=b"")
    proc.stderr = stderr

    # wait() must be awaitable
    proc.wait = AsyncMock(return_value=0)

    return proc
