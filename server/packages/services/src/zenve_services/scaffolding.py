from __future__ import annotations

import json
from pathlib import Path

USER_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {"name", "slug", "github_label", "enabled", "model", "picks_up", "timeout_seconds"}
)

_AGENTS_SKILLS_DIR = ".agents/skills"
_CLAUDE_SKILLS_DIR = ".claude/skills"


class ScaffoldingService:
    def write_agent_files(self, zdir: Path, slug: str, files: dict[str, bytes]) -> None:
        """Write agent files to .zenve/agents/{slug}/ on local disk."""
        agent_out = zdir / "agents" / slug
        for relpath, content in files.items():
            dest = agent_out / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

    def write_agent_files_with_merge(
        self, zdir: Path, slug: str, files: dict[str, bytes]
    ) -> None:
        """Write agent files, preserving user-owned keys in existing settings.json."""
        agent_out = zdir / "agents" / slug
        existing_settings_path = agent_out / "settings.json"
        for relpath, content in files.items():
            if relpath == "settings.json" and existing_settings_path.exists():
                existing_raw = json.loads(existing_settings_path.read_text(encoding="utf-8"))
                new_raw = json.loads(content)
                merged_raw = {
                    **new_raw,
                    **{k: v for k, v in existing_raw.items() if k in USER_OVERRIDE_KEYS},
                }
                content = json.dumps(merged_raw, indent=2).encode()
            dest = agent_out / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

    def update_pipeline(self, zdir: Path, new_entries: dict[str, None]) -> None:
        """Merge new pipeline keys into .zenve/settings.json."""
        try:
            existing_settings: dict = json.loads((zdir / "settings.json").read_bytes())
        except Exception:
            existing_settings = {}
        existing_pipeline: dict = existing_settings.get("pipeline", {})
        merged_pipeline = existing_pipeline | new_entries
        updated_settings = {**existing_settings, "pipeline": merged_pipeline}
        (zdir / "settings.json").write_bytes(json.dumps(updated_settings, indent=2).encode())

    def write_skill_files(
        self, repo_root: Path, skill_id: str, files: dict[str, bytes]
    ) -> None:
        """Write skill files to .agents/skills/{id}/ and create .claude/skills symlink."""
        agent_skills_root = repo_root / _AGENTS_SKILLS_DIR
        claude_skills_root = repo_root / _CLAUDE_SKILLS_DIR
        agent_skills_root.mkdir(parents=True, exist_ok=True)
        claude_skills_root.mkdir(parents=True, exist_ok=True)

        skill_out = agent_skills_root / skill_id
        skill_out.mkdir(parents=True, exist_ok=True)
        for relpath, content in files.items():
            dest = skill_out / relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

        link_path = claude_skills_root / skill_id
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(Path("../../.agents/skills") / skill_id)
