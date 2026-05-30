from __future__ import annotations

import asyncio
import asyncio.subprocess
import json
import logging
import os
import time
from pathlib import Path
from typing import ClassVar

from zenve_adapters.base import BaseAdapter
from zenve_adapters.models import ClaudeCodeConfig, RunContext, RunResult

logger = logging.getLogger(__name__)


class ClaudeCodeAdapter(BaseAdapter):
    """Adapter that spawns the `claude` CLI as a subprocess."""

    adapter_type: ClassVar[str] = "claude_code"

    # ------------------------------------------------------------------
    # Config lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_default_config(cls) -> ClaudeCodeConfig:
        return ClaudeCodeConfig()

    @classmethod
    def validate_config(cls, raw_config: dict) -> ClaudeCodeConfig:
        return ClaudeCodeConfig.model_validate(raw_config)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude",
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

    async def execute(self, ctx: RunContext, cancel_event: asyncio.Event | None = None) -> RunResult:
        start = time.monotonic()
        config = self.validate_config(ctx.adapter_config)

        soul = self.read_file(Path(ctx.agent_dir) / "SOUL.md")
        agents_md = self.read_file(Path(ctx.agent_dir) / "AGENTS.md")

        context = (
            f"# IMPORTANT context:\n"
            f"- agent_id: {ctx.agent_id}\n"
            f"- agent_slug: {ctx.agent_slug}\n"
            f"- agent_name: {ctx.agent_name}\n"
            f"- workspace_slug: {ctx.workspace_slug}\n"
            f"- workspace_id: {ctx.workspace_id}\n"
            f"- workspace_description: {ctx.workspace_description}\n"
            f"- workspace_stack: {', '.join(ctx.workspace_stack) if ctx.workspace_stack else '(unspecified)'}\n"
            f"- workspace_dir: {ctx.workspace_dir}\n"
            f"- agent_dir: {ctx.agent_dir}\n"
            f"- run_id: {ctx.run_id}\n"
            f"- For full workspace context, read: {ctx.workspace_dir}/README.md\n"
        )

        if ctx.heartbeat:
            heartbeat_md = self.read_file(Path(ctx.agent_dir) / "HEARTBEAT.md")
            system_prompt = f"{context}\n\n{soul}\n\n{agents_md}\n\n{heartbeat_md}"
            message = "Heartbeat tick."
        else:
            run_md = self.read_file(Path(ctx.agent_dir) / "RUN.md")
            system_prompt = f"{context}\n\n{soul}\n\n{agents_md}\n\n{run_md}"
            message = ctx.message or "(no message provided)"

        env = {
            **os.environ,
            "ZENVE_AGENT_ID": ctx.agent_id,
            "ZENVE_AGENT_SLUG": ctx.agent_slug,
            "ZENVE_WORKSPACE_SLUG": ctx.workspace_slug,
            "ZENVE_WORKSPACE_ID": ctx.workspace_id,
            "ZENVE_RUN_ID": ctx.run_id,
            **ctx.env_vars,
        }

        args = self.build_cli_args(config, message, system_prompt, ctx.tools)

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ctx.workspace_dir,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,  # 10 MB — Claude can output large JSON lines
        )

        if proc.stdin:
            proc.stdin.write(message.encode())
            await proc.stdin.drain()
            proc.stdin.close()

        full_stdout_lines: list[str] = []
        token_usage: dict | None = None
        outcome: str | None = None
        last_error_message: str | None = None
        last_error_payload: dict | None = None

        assert proc.stdout is not None
        read_task = asyncio.create_task(proc.stdout.readline())
        cancel_task = asyncio.create_task(cancel_event.wait()) if cancel_event else None

        while True:
            tasks: list = [read_task]
            if cancel_task:
                tasks.append(cancel_task)

            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            if cancel_task and cancel_task in done:
                proc.terminate()
                await proc.wait()
                read_task.cancel()
                return RunResult(
                    exit_code=-1,
                    stdout="\n".join(full_stdout_lines),
                    stderr="",
                    duration_seconds=time.monotonic() - start,
                    error="cancelled",
                    outcome=None,
                )

            raw_line = read_task.result()
            if not raw_line:
                break  # EOF — process finished naturally

            line = raw_line.decode(errors="replace").strip()
            if not line:
                read_task = asyncio.create_task(proc.stdout.readline())
                continue
            full_stdout_lines.append(line)

            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("[run:%s] non-JSON output: %s", ctx.run_id, line[:200])
                read_task = asyncio.create_task(proc.stdout.readline())
                continue

            if not isinstance(parsed, dict):
                read_task = asyncio.create_task(proc.stdout.readline())
                continue

            event_type = parsed.get("type")
            event: tuple | None = None

            if event_type == "system":
                captured_session = parsed.get("session_id", "unknown")
                event = (
                    "output",
                    f"Session started: {captured_session}",
                    {"session_id": captured_session},
                )

            elif event_type == "assistant":
                blocks = parsed.get("message", {}).get("content", "")
                if isinstance(blocks, str):
                    if blocks:
                        event = ("output", blocks, None)
                elif isinstance(blocks, list):
                    for block in blocks:
                        if block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                event = ("output", text, None)
                        elif block.get("type") == "tool_use":
                            event = (
                                "tool_call",
                                f"Calling tool: {block.get('name')}",
                                {
                                    "tool": block.get("name"),
                                    "tool_use_id": block.get("id"),
                                    "input": block.get("input", {}),
                                },
                            )
                        if event:
                            ctx.on_event(*event)
                            event = None
                    read_task = asyncio.create_task(proc.stdout.readline())
                    continue

            elif event_type == "user":
                content_blocks = parsed.get("message", {}).get("content", [])
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if block.get("type") == "tool_result":
                            result_content = str(block.get("content", ""))
                            summary = (
                                result_content[:500] + "..."
                                if len(result_content) > 500
                                else result_content
                            )
                            event = (
                                "tool_result",
                                summary,
                                {
                                    "tool_use_id": block.get("tool_use_id"),
                                    "is_error": block.get("is_error", False),
                                    "full_result": result_content,
                                },
                            )
                        if event:
                            ctx.on_event(*event)
                            event = None
                    read_task = asyncio.create_task(proc.stdout.readline())
                    continue

            elif event_type == "result":
                outcome = parsed.get("result") or None
                subtype = parsed.get("subtype")
                is_error = bool(parsed.get("is_error", False))
                if is_error or (subtype and subtype != "success"):
                    msg = f"claude result error: subtype={subtype or 'unknown'}"
                    if outcome:
                        msg = f"{msg} | result={str(outcome)[:300]}"
                    last_error_message = msg
                    last_error_payload = {
                        "subtype": subtype,
                        "is_error": is_error,
                        "result": outcome,
                    }
                    logger.error("[run:%s] %s", ctx.run_id, msg)
                    ctx.on_event("error", msg, {"type": "result_error", "payload": last_error_payload})
                usage = parsed.get("usage", {})
                if usage:
                    token_usage = {
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                        "cost_usd": parsed.get("total_cost_usd"),
                    }
                    event = ("usage", f"Cost: {parsed.get('total_cost_usd')}", token_usage)

            elif event_type == "error":
                payload = {k: v for k, v in parsed.items() if k != "type"}
                msg = self.extract_error_message(payload)
                last_error_message = msg
                last_error_payload = payload
                event = ("error", msg, {"type": "error", "payload": payload})

            if event:
                ctx.on_event(*event)

            read_task = asyncio.create_task(proc.stdout.readline())

        stderr_bytes = await proc.stderr.read() if proc.stderr else b""
        await proc.wait()

        duration = time.monotonic() - start
        stderr = stderr_bytes.decode(errors="replace")
        return_code = proc.returncode or 0

        if return_code != 0:
            logger.error(
                "[run:%s] claude exited with code %s | last_error=%s | stderr=%s",
                ctx.run_id,
                return_code,
                last_error_message,
                stderr.strip()[:1000] or "(empty)",
            )
            stderr_text = stderr.strip()
            if stderr_text and stderr_text != last_error_message:
                ctx.on_event(
                    "error",
                    stderr_text[:1000],
                    {"type": "stderr", "return_code": return_code},
                )
            elif not last_error_message:
                ctx.on_event(
                    "error",
                    f"claude exited with code {return_code}",
                    {"type": "exit", "return_code": return_code},
                )

        error = self.compose_error_text(
            return_code=return_code,
            stderr=stderr,
            last_error_message=last_error_message,
            last_error_payload=last_error_payload,
        )

        return RunResult(
            exit_code=return_code,
            stdout="\n".join(full_stdout_lines),
            stderr=stderr,
            duration_seconds=duration,
            token_usage=token_usage,
            error=error,
            outcome=outcome,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def build_cli_args(
        self,
        config: ClaudeCodeConfig,
        message: str,
        system_prompt: str,
        tools: list[str] | None = None,
    ) -> list[str]:
        args = [
            "claude",
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",
        ]
        args.extend(["--system-prompt", system_prompt])
        if config.model:
            args.extend(["--model", config.model])
        if config.max_turns:
            args.extend(["--max-turns", str(config.max_turns)])
        if config.mode:
            args.extend(["--permission-mode", config.mode])
        if tools:
            args.extend(["--allowedTools", ",".join(tools)])
        return args

    def parse_token_usage(self, stdout: str) -> dict | None:
        """Parse token usage from Claude CLI JSON output."""
        try:
            data = json.loads(stdout)
            usage = data.get("usage") or data.get("token_usage")
            if isinstance(usage, dict):
                return {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cost_usd": usage.get("cost_usd"),
                }
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    @staticmethod
    def extract_error_message(payload: dict) -> str:
        message = payload.get("message")
        if isinstance(message, str) and message:
            return message

        error = payload.get("error")
        if isinstance(error, str) and error:
            return error
        if isinstance(error, dict):
            for key in ("message", "name", "type"):
                value = error.get(key)
                if isinstance(value, str) and value:
                    return value

        for key in ("name", "type"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value

        return "unknown error"

    @classmethod
    def compose_error_text(
        cls,
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
        return f"claude exited with code {return_code}"

    @staticmethod
    def read_file(path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"(file not found: {path.name})"
