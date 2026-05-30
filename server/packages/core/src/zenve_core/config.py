from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from zenve_core.constants import SETTINGS_FILE, ZENVE_DIR
from zenve_core.models.settings import WorkspaceSettings


class ConfigError(RuntimeError):
    """Raised when `.zenve/settings.json` is missing or invalid."""


def zenve_dir(repo_root: Path) -> Path:
    return repo_root / ZENVE_DIR


def load_workspace_settings(repo_root: Path) -> WorkspaceSettings:
    """Read and validate `.zenve/settings.json`.

    Raises ConfigError if the `.zenve/` folder is missing — the CLI never
    scaffolds it; the repo author owns the folder.
    """
    zdir = zenve_dir(repo_root)
    if not zdir.exists():
        raise ConfigError(
            f"Missing `{ZENVE_DIR}/` folder at {repo_root}. "
            "The CLI does not scaffold — author `.zenve/` first."
        )

    settings_path = zdir / SETTINGS_FILE
    if not settings_path.exists():
        raise ConfigError(f"Missing `{ZENVE_DIR}/{SETTINGS_FILE}` at {settings_path}")

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {settings_path}: {exc}") from exc

    try:
        return WorkspaceSettings.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid `{SETTINGS_FILE}`: {exc}") from exc
