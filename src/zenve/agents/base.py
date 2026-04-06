from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from zenve.models.adapter import AdapterConfigBase, RunContext, RunResult


class BaseAdapter(ABC):
    """Contract that every agent runtime adapter must fulfill.

    An adapter is stateless — it holds no per-run state. All execution
    context is passed in via RunContext. A single adapter instance is
    created at startup and reused for all runs of that adapter_type.
    """

    adapter_type: ClassVar[str]

    def name(self) -> str:
        """Return the canonical adapter identifier string (e.g. 'claude_code')."""
        return self.__class__.adapter_type

    # ------------------------------------------------------------------
    # Config lifecycle
    # ------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def get_default_config(cls) -> AdapterConfigBase:
        """Return a default config instance with sensible defaults.

        Called by AgentService.create() when adapter_config is empty or partial.
        The returned model is serialized and stored in Agent.adapter_config.
        """
        ...

    @classmethod
    @abstractmethod
    def validate_config(cls, raw_config: dict) -> AdapterConfigBase:
        """Validate and coerce raw adapter_config dict into the typed config model.

        Called by AgentService.create() and AgentService.update() before
        persisting adapter_config changes. Raises pydantic.ValidationError
        if the config is structurally invalid.
        """
        ...

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute(self, ctx: RunContext) -> RunResult:
        """Execute the agent for one run (manual or heartbeat).

        Called inside a Celery worker. Implementations must handle both run
        types by inspecting ctx.heartbeat.

        Must NOT raise on non-zero subprocess exit codes — those are captured
        in RunResult.exit_code. Only raise for infrastructure failures that
        should trigger a Celery retry.
        """
        ...

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if this adapter's runtime dependency is available.

        Must never raise — return False on any failure.
        """
        ...
