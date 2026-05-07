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
from zenve_adapters.open_code import OpenCodeAdapter
from zenve_models.adapter import RunContext

SOUL_MD = """\
You are a python architect that makes plans.
"""

AGENTS_MD = """\
# Instructions
You are a planning agent you plan even the smallest task. Make sure you add the path to the plan as your last message.
"""

MESSAGE = """\
Make a plan to check if hello.py exists, then if not create it and write a simple python function that prints 'Hello, World!'
"""


async def main() -> None:
    adapter = ClaudeCodeAdapter()
    # adapter = (
    #     OpenCodeAdapter()
    # )  # <-- switch to this adapter to test with OpenCode instead of Claude

    # Confirm the claude CLI is available before running.
    if not await adapter.health_check():
        print("ERROR: `claude` CLI not found or not working. Install it first.")
        return

    with tempfile.TemporaryDirectory() as project_dir:
        agent_dir = Path(project_dir, "agents", "dev")
        agent_dir.mkdir(parents=True, exist_ok=True)

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
            agent_id="dev-01",
            agent_slug="dev",
            agent_name="Devy",
            agent_dir=str(agent_dir.resolve()),
            project_dir=str(project_dir),
            project_slug="logzai",
            run_id="run-001",
            adapter_type="claude_code",
            adapter_config={"model": "claude-sonnet-4-6", "max_turns": 10, "mode": "plan"},
            message=MESSAGE,
            heartbeat=False,
            tools=["Read", "Edit", "Bash", "ExitPlanMode"],
            on_event=on_event,
        )

        print(f"Running task: {ctx.message!r}\n")
        # print(f"Running context: {ctx}\n")
        result = await adapter.execute(ctx)

    print(f"\nExit code : {result.exit_code}")
    print(f"Duration  : {result.duration_seconds:.2f}s")
    # print(f"Result   : {result}")

    if result.token_usage:
        print(f"Tokens    : {result.token_usage}")
    if result.error:
        print(f"Stderr    :\n{result.stderr.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
