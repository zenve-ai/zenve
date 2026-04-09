"""Shared test helpers for the Zenve test suite.

Import explicitly via ``from zenve_utils.testing import ...`` — these
symbols are intentionally *not* re-exported from the package root.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock


class AsyncLineIter:
    """Async iterator over a list of raw bytes lines (simulates proc.stdout)."""

    def __init__(self, lines: list[bytes]) -> None:
        self.lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self.lines)
        except StopIteration:
            raise StopAsyncIteration from None


def make_proc(
    lines: list[bytes],
    stderr: bytes = b"",
    returncode: int = 0,
) -> MagicMock:
    """Return a mock asyncio subprocess whose stdout yields *lines*."""
    proc = MagicMock()
    proc.stdout = AsyncLineIter(lines)
    proc.returncode = returncode
    proc.wait = AsyncMock(return_value=None)

    stderr_stream = MagicMock()
    stderr_stream.read = AsyncMock(return_value=stderr)
    proc.stderr = stderr_stream

    stdin = MagicMock()
    stdin.drain = AsyncMock(return_value=None)
    proc.stdin = stdin

    return proc


def json_line(payload: dict) -> bytes:
    """Encode a dict as a JSON bytes line (terminated with ``\\n``)."""
    return (json.dumps(payload) + "\n").encode()
