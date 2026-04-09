"""
Simple example: run one task with the ClaudeCodeAdapter.

Usage:
    uv run python examples/run_claude_code.py

Requirements:
    - `claude` CLI installed and authenticated
    - An agent directory with SOUL.md and AGENTS.md files
      (the example creates temporary ones automatically)
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_models.adapter import RunContext

SOUL_MD = """\
You are a helpful assistant that answers questions concisely.
"""

AGENTS_MD = """\
# Instructions
Answer the user's question directly and briefly.
"""

MESSAGE = """\
Check if hello.py exists, then if not create it and write a simple python function that prints 'Hello, World!'
"""


async def main() -> None:
    adapter = ClaudeCodeAdapter()

    # Confirm the claude CLI is available before running.
    if not await adapter.health_check():
        print("ERROR: `claude` CLI not found or not working. Install it first.")
        return

    with tempfile.TemporaryDirectory() as agent_dir:
        Path(agent_dir, "SOUL.md").write_text(SOUL_MD)
        Path(agent_dir, "AGENTS.md").write_text(AGENTS_MD)

        print(f"Agent directory: {agent_dir}")

        def on_event(
            event_type: str, content: str | None = None, metadata: dict | None = None
        ) -> None:
            print(f"[{event_type}] {content or ''}")
            print(f"{metadata or ''}")
            print("=" * 60)

        ctx = RunContext(
            agent_dir=agent_dir,
            agent_id="dev-01",
            agent_slug="dev",
            agent_name="Devy",
            org_id="1",
            org_slug="logzai",
            run_id="run-001",
            adapter_type="open_code",
            adapter_config={
                "max_turns": 5,
            },
            message=MESSAGE,
            heartbeat=False,
            gateway_url="http://localhost:8000",
            agent_token="",
            tools=["Read", "Write", "Edit", "Bash"],
            on_event=on_event,
        )

        print(f"Running task: {ctx.message!r}\n")
        result = await adapter.execute(ctx)

    print(f"\nExit code : {result.exit_code}")
    print(f"Duration  : {result.duration_seconds:.2f}s")
    if result.token_usage:
        print(f"Tokens    : {result.token_usage}")
    if result.error:
        print(f"Stderr    :\n{result.stderr.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
