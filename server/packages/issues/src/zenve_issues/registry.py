from __future__ import annotations

from zenve_issues.base import BaseIssueAdapter


class IssueAdapterRegistry:
    """Maps adapter_type strings to configured BaseIssueAdapter instances.

    Usage:
        registry = IssueAdapterRegistry()
        registry.add(GitHubIssueAdapter(GitHubIssueConfig(repo="org/repo")))
        adapter = registry.get("github")
        issues = adapter.list()
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseIssueAdapter] = {}

    def add(self, adapter: BaseIssueAdapter) -> None:
        """Register an adapter under its adapter_type key.

        Raises ValueError if an adapter for that type is already registered.
        """
        key = adapter.name()
        if key in self._adapters:
            raise ValueError(f"Adapter already registered: {key!r}")
        self._adapters[key] = adapter

    def get(self, adapter_type: str) -> BaseIssueAdapter:
        """Return the registered adapter for the given type.

        Raises KeyError if no adapter is registered for that type.
        """
        if adapter_type not in self._adapters:
            raise KeyError(f"Unknown adapter_type: {adapter_type!r}")
        return self._adapters[adapter_type]

    def has(self, adapter_type: str) -> bool:
        return adapter_type in self._adapters

    def known_types(self) -> list[str]:
        return sorted(self._adapters.keys())

    def health_check_all(self) -> dict[str, bool]:
        """Run health_check() on every registered adapter."""
        return {name: adapter.health_check() for name, adapter in self._adapters.items()}
