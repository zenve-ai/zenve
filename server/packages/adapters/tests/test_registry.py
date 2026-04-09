from __future__ import annotations

import pytest

from zenve_adapters.base import BaseAdapter
from zenve_adapters.registry import AdapterRegistry
from zenve_models.adapter import AdapterConfigBase, RunContext, RunResult


class StubAdapter(BaseAdapter):
    adapter_type = "stub"

    @classmethod
    def get_default_config(cls) -> AdapterConfigBase:
        return AdapterConfigBase()

    @classmethod
    def validate_config(cls, raw_config: dict) -> AdapterConfigBase:
        return AdapterConfigBase()

    async def execute(self, ctx: RunContext) -> RunResult:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True


def test_register_and_get():
    registry = AdapterRegistry()
    adapter = StubAdapter()

    registry.register(adapter)

    assert registry.has("stub")
    assert registry.get("stub") is adapter
    assert registry.known_types() == ["stub"]


def test_register_duplicate_raises():
    registry = AdapterRegistry()
    registry.register(StubAdapter())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(StubAdapter())


def test_get_unknown_raises():
    registry = AdapterRegistry()

    with pytest.raises(KeyError, match="Unknown adapter_type"):
        registry.get("nonexistent")
