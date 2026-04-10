from __future__ import annotations

import asyncio
import asyncio.subprocess
import json
import os
import time
from pathlib import Path
from typing import ClassVar

from zenve_adapters.base import BaseAdapter
from zenve_models.adapter import OpenCodeConfig, RunContext, RunResult


class OpenCodeAdapter(BaseAdapter):
    """Adapter that spawns the `opencode` CLI as a subprocess."""

    adapter_type: ClassVar[str] = "open_code"

    # ------------------------------------------------------------------
    # Config lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_default_config(cls) -> OpenCodeConfig:
        return OpenCodeConfig()

    @classmethod
    def validate_config(cls, raw_config: dict) -> OpenCodeConfig:
        return OpenCodeConfig.model_validate(raw_config)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "opencode",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, ctx: RunContext) -> RunResult:
        start = time.monotonic()
        config = self.validate_config(ctx.adapter_config)

        soul = self.read_file(Path(ctx.agent_dir) / "SOUL.md")
        agents_md = self.read_file(Path(ctx.agent_dir) / "AGENTS.md")

        context = (
            f"# IMPORTANT context:\n"
            f"- agent_id: {ctx.agent_id}\n"
            f"- agent_slug: {ctx.agent_slug}\n"
            f"- agent_name: {ctx.agent_name}\n"
            f"- org_id: {ctx.org_id}\n"
            f"- org_slug: {ctx.org_slug}\n"
            f"- run_id: {ctx.run_id}\n"
            f"- gateway_url: {ctx.gateway_url}\n"
        )

        if ctx.heartbeat:
            heartbeat_md = self.read_file(Path(ctx.agent_dir) / "HEARTBEAT.md")
            system_prompt = f"{context}\n\n{soul}\n\n{agents_md}\n\n{heartbeat_md}"
            message = "Heartbeat tick."
        else:
            run_md = self.read_file(Path(ctx.agent_dir) / "RUN.md")
            system_prompt = f"{context}\n\n{soul}\n\n{agents_md}\n\n{run_md}"
            message = ctx.message or "(no message provided)"

        stdin_payload = f"{system_prompt}\n\n---\n\n{message}"

        env = {
            **os.environ,
            "GATEWAY_URL": ctx.gateway_url,
            "GATEWAY_AGENT_TOKEN": ctx.agent_token,
            "GATEWAY_AGENT_ID": ctx.agent_id,
            "GATEWAY_AGENT_SLUG": ctx.agent_slug,
            "GATEWAY_ORG_SLUG": ctx.org_slug,
            "GATEWAY_RUN_ID": ctx.run_id,
            "OPENCODE_PERMISSION": '{"*": "allow"}',
            "OPENCODE_DISABLE_PROJECT_CONFIG": "true",
            **ctx.env_vars,
        }

        args = self.build_cli_args(config)

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ctx.agent_dir,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if proc.stdin:
            proc.stdin.write(stdin_payload.encode())
            await proc.stdin.drain()
            proc.stdin.close()

        full_stdout_lines: list[str] = []

        token_usage: dict | None = None
        session_id: str | None = None

        if proc.stdout:
            async for raw_line in proc.stdout:
                line = raw_line.decode(errors="replace").strip()
                if not line:
                    continue
                full_stdout_lines.append(line)

                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    print(f"[run:{ctx.run_id}] output: {line}")
                    continue

                event_type = parsed.get("type")

                # Track session ID from first event that carries one
                evt_session = parsed.get("sessionID", "")
                if evt_session and session_id is None:
                    session_id = evt_session
                    ctx.on_event(
                        "output",
                        f"Session started: {session_id}",
                        {"session_id": session_id},
                    )

                event: tuple | None = None

                if event_type == "text":
                    part = parsed.get("part", {})
                    text = part.get("text", "")
                    if text:
                        event = ("output", text, None)

                elif event_type == "tool_use":
                    part = parsed.get("part", {})
                    tool_name = part.get("name", "unknown")
                    tool_input = part.get("input", {})
                    state = part.get("state", {})
                    status = state.get("status", "")
                    error_text = state.get("error", "")

                    meta: dict = {
                        "tool": tool_name,
                        "input": tool_input,
                    }
                    if status == "error" and error_text:
                        meta["error"] = error_text
                        event = ("tool_call", f"Tool error: {tool_name}: {error_text}", meta)
                    else:
                        event = ("tool_call", f"Calling tool: {tool_name}", meta)

                elif event_type == "step_finish":
                    part = parsed.get("part", {})
                    tokens = part.get("tokens", {})
                    cache = tokens.get("cache", {})
                    token_usage = {
                        "input_tokens": tokens.get("input", 0),
                        "output_tokens": tokens.get("output", 0),
                        "reasoning_tokens": tokens.get("reasoning", 0),
                        "cache_read_input_tokens": cache.get("read", 0),
                        "cost_usd": part.get("cost"),
                    }
                    event = ("usage", None, token_usage)

                elif event_type == "error":
                    error = parsed.get("error", parsed.get("message", "unknown error"))
                    if isinstance(error, dict):
                        msg = error.get("message", "") or error.get("name", "") or str(error)
                    else:
                        msg = str(error)
                    event = ("error", msg, {"type": "error"})

                if event:
                    ctx.on_event(*event)

        stderr_bytes = await proc.stderr.read() if proc.stderr else b""
        await proc.wait()

        duration = time.monotonic() - start
        stderr = stderr_bytes.decode(errors="replace")

        return RunResult(
            exit_code=proc.returncode or 0,
            stdout="\n".join(full_stdout_lines),
            stderr=stderr,
            duration_seconds=duration,
            token_usage=token_usage,
            error=stderr if proc.returncode != 0 else None,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def build_cli_args(self, config: OpenCodeConfig) -> list[str]:
        args = [
            "opencode",
            "run",
            "--format",
            config.output_format,
        ]
        if config.model:
            args.extend(["--model", config.model])
        return args

    @staticmethod
    def read_file(path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"(file not found: {path.name})"
