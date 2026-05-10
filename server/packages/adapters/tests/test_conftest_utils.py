"""Tests for conftest helpers: json_line and make_proc."""
from __future__ import annotations

import json

import pytest

from conftest import json_line, make_proc


def test_json_line_encodes_dict():
    result = json_line({"type": "system", "session_id": "s1"})
    assert isinstance(result, bytes)
    decoded = json.loads(result.decode())
    assert decoded == {"type": "system", "session_id": "s1"}
    assert result.endswith(b"\n")


def test_json_line_nested():
    obj = {"a": {"b": [1, 2, 3]}}
    result = json_line(obj)
    assert json.loads(result) == obj


def test_make_proc_has_returncode():
    proc = make_proc([])
    assert proc.returncode == 0


def test_make_proc_stdin_is_mock():
    proc = make_proc([])
    assert proc.stdin is not None


def test_make_proc_stderr_has_read():
    proc = make_proc([])
    assert proc.stderr is not None


@pytest.mark.asyncio
async def test_make_proc_stdout_yields_lines():
    lines = [json_line({"type": "text", "value": i}) for i in range(3)]
    proc = make_proc(lines)
    collected = []
    async for raw_line in proc.stdout:
        collected.append(raw_line)
    assert collected == lines


@pytest.mark.asyncio
async def test_make_proc_stdout_empty():
    proc = make_proc([])
    collected = []
    async for raw_line in proc.stdout:
        collected.append(raw_line)
    assert collected == []


@pytest.mark.asyncio
async def test_make_proc_wait_returns_zero():
    proc = make_proc([])
    result = await proc.wait()
    assert result == 0


@pytest.mark.asyncio
async def test_make_proc_stderr_read_returns_empty():
    proc = make_proc([])
    result = await proc.stderr.read()
    assert result == b""


@pytest.mark.asyncio
async def test_make_proc_stdin_drain_is_awaitable():
    proc = make_proc([])
    await proc.stdin.drain()  # should not raise
