from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

RUNTIME_CONFIG_PATH = Path.home() / ".zenve" / "settings.json"
ENV_ISSUES_ADAPTER = "ZENVE_ISSUES_ADAPTER"


class RuntimeConfig(BaseModel):
    issues_adapter: str = "github"

    @classmethod
    def load(cls) -> RuntimeConfig:
        """Load from ~/.zenve/config.json, then override with env vars."""
        data: dict = {}
        if RUNTIME_CONFIG_PATH.exists():
            try:
                data = json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        config = cls.model_validate(data)
        if adapter := os.environ.get(ENV_ISSUES_ADAPTER):
            config.issues_adapter = adapter
        return config
