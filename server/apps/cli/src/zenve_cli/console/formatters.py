from __future__ import annotations

import json
from collections.abc import Callable

from rich.markup import escape
from rich.text import Text

TOOL_FORMATTERS: dict[str, Callable[[dict | None], Text]] = {}


def format_tool_args(payload: dict, max_str_len: int = 60) -> str:
    parts: list[str] = []
    for k, v in payload.items():
        if isinstance(v, str):
            truncated = v if len(v) <= max_str_len else v[: max_str_len - 3] + "..."
            parts.append(f'{k}="{truncated}"')
        elif isinstance(v, (int, float, bool)):
            parts.append(f"{k}={v}")
        else:
            s = json.dumps(v, separators=(",", ":"))
            if len(s) > max_str_len:
                s = s[: max_str_len - 3] + "..."
            parts.append(f"{k}={s}")
    return "  ".join(parts)


def make_tool_text(tool: str, payload: dict | None) -> Text:
    t = Text()
    t.append("▶ ", style="cyan")
    t.append(tool, style="bold")
    if payload:
        t.append("  ")
        t.append(escape(format_tool_args(payload)), style="dim")
    return t


def fmt_read(payload: dict | None) -> Text:
    p = payload or {}
    path = p.get("filePath") or p.get("path", "")
    t = Text()
    t.append("▶ ", style="cyan")
    t.append("read", style="bold")
    t.append("  ")
    t.append(str(path), style="dim")
    return t


def fmt_bash(payload: dict | None) -> Text:
    cmd = (payload or {}).get("command", "")
    if len(cmd) > 80:
        cmd = cmd[:77] + "..."
    t = Text()
    t.append("▶ ", style="cyan")
    t.append("bash", style="bold")
    t.append("  ")
    t.append(cmd, style="dim")
    return t


TOOL_FORMATTERS["read"] = fmt_read
TOOL_FORMATTERS["bash"] = fmt_bash
