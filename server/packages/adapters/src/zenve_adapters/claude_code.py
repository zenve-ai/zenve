from __future__ import annotations

import asyncio
import asyncio.subprocess
import json
import os
import time
from pathlib import Path
from typing import ClassVar

from zenve_adapters.base import BaseAdapter
from zenve_models.adapter import ClaudeCodeConfig, RunContext, RunResult


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

        soul = self._read_file(Path(ctx.agent_dir) / "SOUL.md")
        agents_md = self._read_file(Path(ctx.agent_dir) / "AGENTS.md")

        if ctx.heartbeat:
            heartbeat_md = self._read_file(Path(ctx.agent_dir) / "HEARTBEAT.md")
            message = (
                f"{agents_md}\n\n---\n\nHeartbeat tick. Review your checklist:\n\n{heartbeat_md}"
            )
        else:
            message = f"{agents_md}\n\n---\n\n{ctx.message or '(no message provided)'}"

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

        args = self._build_cli_args(config, message, soul, ctx.tools)
        print(f"Args: {args}")

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ctx.agent_dir,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate(input=message.encode())

        duration = time.monotonic() - start
        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")

        token_usage = self._parse_token_usage(stdout)

        return RunResult(
            exit_code=proc.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            token_usage=token_usage,
            error=stderr if proc.returncode != 0 else None,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_cli_args(
        self,
        config: ClaudeCodeConfig,
        message: str,
        system_prompt: str,
        tools: list[str] | None = None,
    ) -> list[str]:
        args = [
            "claude",
            "--print",
            "--output-format",
            config.output_format,
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

    def _parse_token_usage(self, stdout: str) -> dict | None:
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
    def _read_file(path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"(file not found: {path.name})"
