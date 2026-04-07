from __future__ import annotations

import asyncio

from zenve_agents.base import BaseAdapter


class AdapterRegistry:
    """Maps adapter_type strings to stateless BaseAdapter instances.

    Created once in api/lifespan.py and stored on app.state.adapter_registry.

    Usage:
        registry = AdapterRegistry()
        registry.register(ClaudeCodeAdapter())
        adapter = registry.get("claude_code")
        result = await adapter.execute(ctx)
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        """Register an adapter instance under its adapter_type key.

        Raises ValueError if an adapter for that type is already registered.
        """
        key = adapter.name()
        if key in self._adapters:
            raise ValueError(f"Adapter already registered: {key!r}")
        self._adapters[key] = adapter

    def get(self, adapter_type: str) -> BaseAdapter:
        """Return the registered adapter for the given type.

        Raises KeyError if no adapter is registered for that type.
        AgentService catches this and converts it to an HTTP 422.
        """
        if adapter_type not in self._adapters:
            raise KeyError(f"Unknown adapter_type: {adapter_type!r}")
        return self._adapters[adapter_type]

    def has(self, adapter_type: str) -> bool:
        """Return True if an adapter is registered for the given type."""
        return adapter_type in self._adapters

    def known_types(self) -> list[str]:
        """Return sorted list of registered adapter_type strings."""
        return sorted(self._adapters.keys())

    async def health_check_all(self) -> dict[str, bool]:
        """Run health_check() on every registered adapter concurrently.

        Returns a dict mapping adapter_type → bool. Used by GET /health.
        """
        results = await asyncio.gather(
            *[adapter.health_check() for adapter in self._adapters.values()],
            return_exceptions=True,
        )
        return {
            name: (result is True)
            for name, result in zip(self._adapters.keys(), results, strict=True)
        }
