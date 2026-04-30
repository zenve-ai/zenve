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
            f"- project_slug: {ctx.project_slug}\n"
            f"- project_description: {ctx.project_description}\n"
            f"- project_dir: {ctx.project_dir}\n"
            f"- agent_dir: {ctx.agent_dir}\n"
            f"- run_id: {ctx.run_id}\n"
            f"- For full project context, read: {ctx.project_dir}/README.md\n"
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
            "ZENVE_AGENT_ID": ctx.agent_id,
            "ZENVE_AGENT_SLUG": ctx.agent_slug,
            "ZENVE_PROJECT_SLUG": ctx.project_slug,
            "ZENVE_RUN_ID": ctx.run_id,
            "OPENCODE_PERMISSION": '{"*": "allow"}',
            "OPENCODE_DISABLE_PROJECT_CONFIG": "true",
            **ctx.env_vars,
        }

        args = self.build_cli_args(config)

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ctx.project_dir,
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

        session_started = False
        token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "cache_read_input_tokens": 0,
            "cost_usd": 0.0,
        }
        saw_usage = False
        last_text: str | None = None
        outcome: str | None = None
        last_error_message: str | None = None
        last_error_payload: dict | None = None

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

                event: tuple | None = None

                if event_type == "step_start":
                    evt_session = parsed.get("sessionID", "")
                    if evt_session and not session_started:
                        session_started = True
                        event = (
                            "output",
                            f"Session started: {evt_session}",
                            {"session_id": evt_session},
                        )

                elif event_type == "text":
                    part = parsed.get("part", {})
                    text = part.get("text", "")
                    if text:
                        last_text = text
                        event = ("output", text, None)

                elif event_type == "tool_use":
                    part = parsed.get("part", {})
                    state = part.get("state", {})
                    tool_name = self.extract_tool_name(parsed, part, state)
                    tool_input = self.extract_tool_input(parsed, part, state)
                    status = state.get("status", "")
                    error_text = state.get("error", "")

                    meta: dict = {
                        "tool": tool_name,
                        "input": tool_input,
                    }
                    if tool_name == "unknown" or not tool_input:
                        meta["raw_part"] = part
                    if status == "error" and error_text:
                        meta["error"] = error_text
                        event = ("tool_call", f"Tool error: {tool_name}: {error_text}", meta)
                    else:
                        event = ("tool_call", f"Calling tool: {tool_name}", meta)

                elif event_type == "step_finish":
                    part = parsed.get("part", {})
                    if part.get("reason") == "stop" and last_text:
                        outcome = last_text
                    tokens = part.get("tokens", {})
                    cache = tokens.get("cache", {})
                    step_usage = {
                        "input_tokens": tokens.get("input", 0),
                        "output_tokens": tokens.get("output", 0),
                        "reasoning_tokens": tokens.get("reasoning", 0),
                        "cache_read_input_tokens": cache.get("read", 0),
                        "cost_usd": part.get("cost") or 0,
                    }
                    token_usage = self.add_usage_totals(token_usage, step_usage)
                    saw_usage = True

                elif event_type == "error":
                    error = parsed.get("error", parsed.get("message", "unknown error"))
                    if isinstance(error, dict):
                        msg = error.get("message", "") or error.get("name", "") or str(error)
                    else:
                        msg = str(error)
                    last_error_message = msg
                    last_error_payload = parsed
                    event = ("error", msg, {"type": "error", "payload": parsed})

                if event:
                    ctx.on_event(*event)

        stderr_bytes = await proc.stderr.read() if proc.stderr else b""
        await proc.wait()

        if saw_usage:
            ctx.on_event("usage", None, token_usage)

        duration = time.monotonic() - start
        stderr = stderr_bytes.decode(errors="replace")
        error = self.compose_error_text(
            return_code=proc.returncode or 0,
            stderr=stderr,
            last_error_message=last_error_message,
            last_error_payload=last_error_payload,
        )

        return RunResult(
            exit_code=proc.returncode or 0,
            stdout="\n".join(full_stdout_lines),
            stderr=stderr,
            duration_seconds=duration,
            token_usage=token_usage if saw_usage else None,
            error=error,
            outcome=outcome,
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

    @staticmethod
    def extract_tool_name(parsed: dict, part: dict, state: dict) -> str:
        """Best-effort extraction because OpenCode tool_use payloads vary by version."""
        candidates = [
            part.get("name"),
            part.get("tool"),
            part.get("tool_name"),
            part.get("toolName"),
            parsed.get("name"),
            parsed.get("tool"),
            parsed.get("tool_name"),
            state.get("name"),
            state.get("tool"),
        ]

        for candidate in candidates:
            if isinstance(candidate, str) and candidate:
                return candidate
            if isinstance(candidate, dict):
                nested = (
                    candidate.get("name")
                    or candidate.get("tool")
                    or candidate.get("tool_name")
                    or candidate.get("toolName")
                )
                if isinstance(nested, str) and nested:
                    return nested

        return "unknown"

    @staticmethod
    def extract_tool_input(parsed: dict, part: dict, state: dict) -> dict:
        """Best-effort extraction because OpenCode tool args vary by model/version."""
        candidates = [
            part.get("input"),
            state.get("input"),
            part.get("args"),
            state.get("args"),
            parsed.get("input"),
            parsed.get("args"),
        ]

        tool_value = part.get("tool")
        if isinstance(tool_value, dict):
            candidates.extend(
                [
                    tool_value.get("input"),
                    tool_value.get("args"),
                ]
            )

        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate

        return {}

    @staticmethod
    def add_usage_totals(total: dict, step: dict) -> dict:
        return {
            "input_tokens": total.get("input_tokens", 0) + step.get("input_tokens", 0),
            "output_tokens": total.get("output_tokens", 0) + step.get("output_tokens", 0),
            "reasoning_tokens": total.get("reasoning_tokens", 0)
            + step.get("reasoning_tokens", 0),
            "cache_read_input_tokens": total.get("cache_read_input_tokens", 0)
            + step.get("cache_read_input_tokens", 0),
            "cost_usd": round(total.get("cost_usd", 0) + step.get("cost_usd", 0), 10),
        }

    @staticmethod
    def compose_error_text(
        *,
        return_code: int,
        stderr: str,
        last_error_message: str | None,
        last_error_payload: dict | None,
    ) -> str | None:
        if return_code == 0:
            return None

        stderr_text = stderr.strip()
        if stderr_text and last_error_message and last_error_message not in stderr_text:
            return f"{last_error_message}\n\nstderr:\n{stderr_text}"
        if stderr_text:
            return stderr_text
        if last_error_message:
            details = ""
            if last_error_payload:
                details = json.dumps(last_error_payload, ensure_ascii=True)
            return (
                f"{last_error_message} | details: {details}"
                if details and details != "{}"
                else last_error_message
            )
        return f"opencode exited with code {return_code}"
