from __future__ import annotations

import json
import os
from pathlib import Path

from runtime.models.settings import GlobalSettings, GlobalSettingsUpdate

GLOBAL_SETTINGS_PATH = Path.home() / ".zenve" / "settings.json"


class SettingsService:
    def __init__(self, path: Path | None = None):
        self.path = path or GLOBAL_SETTINGS_PATH

    def get(self) -> GlobalSettings:
        if not self.path.exists():
            return GlobalSettings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return GlobalSettings()
        return GlobalSettings.model_validate(data)

    def update(self, body: GlobalSettingsUpdate) -> GlobalSettings:
        current = self.get()
        data = current.model_dump()
        patch = body.model_dump(exclude_none=True)
        data.update(patch)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
        return GlobalSettings.model_validate(data)
