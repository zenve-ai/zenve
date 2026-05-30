from __future__ import annotations


class CoreError(RuntimeError):
    pass


class AgentNotFoundError(CoreError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"Agent not found or disabled: {slug!r}")
