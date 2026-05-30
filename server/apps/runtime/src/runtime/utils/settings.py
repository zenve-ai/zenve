from __future__ import annotations

import json
from pathlib import Path


def read_issues_adapter(workspace_dir: Path) -> str | None:
    """Read issues.adapter from .zenve/settings.json without loading the full model."""
    settings_path = workspace_dir / ".zenve" / "settings.json"
    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
        return raw.get("issues", {}).get("adapter") or None
    except (FileNotFoundError, json.JSONDecodeError):
        return None
