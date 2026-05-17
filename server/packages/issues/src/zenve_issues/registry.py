from __future__ import annotations

from zenve_issues.base import BaseIssueAdapter


class IssueAdapterRegistry:
    """Maps adapter_type strings to stateless BaseIssueAdapter instances.

    Usage:
        registry = IssueAdapterRegistry()
        registry.register(GitHubIssueAdapter())
        adapter = registry.get("github")
        issues = adapter.list(config)
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseIssueAdapter] = {}

    def register(self, adapter: BaseIssueAdapter) -> None:
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

    def health_check_all(self, configs: dict[str, dict]) -> dict[str, bool]:
        """Run health_check() on every registered adapter.

        configs: dict mapping adapter_type → raw config dict.
        Returns a dict mapping adapter_type → bool.
        """
        results: dict[str, bool] = {}
        for name, adapter in self._adapters.items():
            raw = configs.get(name, {})
            try:
                cfg = adapter.validate_config(raw)
                results[name] = adapter.health_check(cfg)
            except Exception:
                results[name] = False
        return results
