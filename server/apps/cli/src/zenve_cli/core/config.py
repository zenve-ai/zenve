from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from zenve_cli.models.settings import ProjectSettings

ZENVE_DIR_NAME = ".zenve"
SETTINGS_FILE = "settings.json"


class ConfigError(RuntimeError):
    """Raised when `.zenve/settings.json` is missing or invalid."""


def zenve_dir(repo_root: Path) -> Path:
    return repo_root / ZENVE_DIR_NAME


def load_project_settings(repo_root: Path) -> ProjectSettings:
    """Read and validate `.zenve/settings.json`.

    Raises ConfigError if the `.zenve/` folder is missing — the CLI never
    scaffolds it; the repo author owns the folder.
    """
    zdir = zenve_dir(repo_root)
    if not zdir.exists():
        raise ConfigError(
            f"Missing `{ZENVE_DIR_NAME}/` folder at {repo_root}. "
            "The CLI does not scaffold — author `.zenve/` first."
        )

    settings_path = zdir / SETTINGS_FILE
    if not settings_path.exists():
        raise ConfigError(f"Missing `{ZENVE_DIR_NAME}/{SETTINGS_FILE}` at {settings_path}")

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {settings_path}: {exc}") from exc

    try:
        return ProjectSettings.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid `{SETTINGS_FILE}`: {exc}") from exc
