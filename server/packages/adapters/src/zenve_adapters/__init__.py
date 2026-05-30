from .base import BaseAdapter
from .claude_code import ClaudeCodeAdapter
from .models import (
    AdapterConfigBase,
    AnthropicAPIConfig,
    ClaudeCodeConfig,
    CodexConfig,
    OpenCodeConfig,
    RunContext,
    RunResult,
)
from .open_code import OpenCodeAdapter
from .registry import AdapterRegistry


def build_default_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(ClaudeCodeAdapter())
    registry.register(OpenCodeAdapter())
    return registry


__all__ = [
    "AdapterRegistry",
    "AdapterConfigBase",
    "AnthropicAPIConfig",
    "BaseAdapter",
    "ClaudeCodeConfig",
    "ClaudeCodeAdapter",
    "CodexConfig",
    "OpenCodeAdapter",
    "OpenCodeConfig",
    "RunContext",
    "RunResult",
    "build_default_registry",
]
