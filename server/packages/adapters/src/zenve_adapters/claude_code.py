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
from zenve_models.adapter import ClaudeCodeConfig, RunContext, RunResult

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

        env = {
            **os.environ,
            "GATEWAY_URL": ctx.gateway_url,
            "GATEWAY_AGENT_TOKEN": ctx.agent_token,
            "GATEWAY_AGENT_ID": ctx.agent_id,
            "GATEWAY_AGENT_SLUG": ctx.agent_slug,
            "GATEWAY_ORG_SLUG": ctx.org_slug,
            "GATEWAY_RUN_ID": ctx.run_id,
            **ctx.env_vars,
        }

        args = self.build_cli_args(config, message, system_prompt, ctx.tools)

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ctx.agent_dir,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if proc.stdin:
            proc.stdin.write(message.encode())
            await proc.stdin.drain()
            proc.stdin.close()

        full_stdout_lines: list[str] = []
        token_usage: dict | None = None
        outcome: str | None = None

        async for raw_line in proc.stdout:
            line = raw_line.decode(errors="replace").strip()
            if not line:
                continue
            full_stdout_lines.append(line)

            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("[run:%s] non-JSON output: %s", ctx.run_id, line[:200])
                continue

            if not isinstance(parsed, dict):
                continue

            event_type = parsed.get("type")
            event: tuple | None = None

            if event_type == "system":
                session_id = parsed.get("session_id", "unknown")
                event = ("output", f"Session started: {session_id}", {"session_id": session_id})

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
                    continue

            elif event_type == "user":
                content_blocks = parsed.get("message", {}).get("content", [])
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if block.get("type") == "tool_result":
                            result_content = str(block.get("content", ""))
                            summary = result_content[:500] + "..." if len(result_content) > 500 else result_content
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
                    continue

            elif event_type == "result":
                outcome = parsed.get("result") or None
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
                msg = parsed.get("message", "unknown error")
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
        if config.max_tokens is not None:
            args.extend(["--max-tokens", str(config.max_tokens)])
        if config.max_turns:
            args.extend(["--max-turns", str(config.max_turns)])
        if tools is not None:
            # Explicit tool list: auto-approve these, deny everything else
            args.extend(["--allowedTools", ",".join(tools)])
        else:
            # No tool restrictions: skip all permission prompts
            args.append("--dangerously-skip-permissions")
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
    def read_file(path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"(file not found: {path.name})"
