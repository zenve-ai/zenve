from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base config
# ---------------------------------------------------------------------------


class AdapterConfigBase(BaseModel):
    """Base class for all adapter-specific configuration models.

    Stored as JSON in Agent.adapter_config. Each adapter defines its own
    config class inheriting from this.
    """

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Per-adapter config models
# ---------------------------------------------------------------------------


class ClaudeCodeConfig(AdapterConfigBase):
    """Config for the claude_code adapter (spawns `claude` CLI)."""

    model: str = "claude-sonnet-4-6"
    max_tokens: int | None = None
    max_turns: int = 10
    output_format: str = "stream-json"


class CodexConfig(AdapterConfigBase):
    """Config for the codex adapter (spawns `codex` CLI)."""

    model: str = "o4-mini"
    max_tokens: int | None = None
    approval_mode: str = "suggest"


class OpenCodeConfig(AdapterConfigBase):
    """Config for the open_code adapter (spawns `opencode` CLI)."""

    model: str = ""
    max_tokens: int | None = None
    steps: int = 10
    output_format: str = "json"


class AnthropicAPIConfig(AdapterConfigBase):
    """Config for the anthropic_api adapter (calls Anthropic API directly)."""

    model: str = "claude-opus-4-5"
    max_tokens: int = 4096
    temperature: float = 1.0
    system_prompt_override: str | None = None


# ---------------------------------------------------------------------------
# Run data models
# ---------------------------------------------------------------------------


@dataclass
class RunContext:
    """All context needed to execute one agent run.

    Built by services/run_context.py:build_run_context() from Agent ORM model.
    Passed directly into BaseAdapter.execute().
    """

    agent_dir: str
    agent_id: str
    agent_slug: str
    agent_name: str
    org_id: str
    org_slug: str
    run_id: str
    adapter_type: str
    adapter_config: dict
    message: str | None
    heartbeat: bool
    gateway_url: str
    agent_token: str  # short-lived JWT (Chunk 09); empty string until then
    tools: list[str] | None = None  # None = all tools allowed
    env_vars: dict = field(default_factory=dict)
    on_event: Callable[[str, str | None, dict | None], None] = field(default=lambda *a, **kw: None)


@dataclass
class RunResult:
    """Result of one completed agent run.

    Returned by BaseAdapter.execute(). Stored in the Run ORM record and
    written to disk as a transcript.
    """

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    token_usage: dict | None = None  # {input_tokens, output_tokens, cost_usd}
    error: str | None = None
