from pathlib import Path

from zenve_config.settings import Settings


class FilesystemService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def read_agent_file(self, agent_dir: str, file_path: str) -> str:
        """Read a file relative to agent_dir. Raises ValueError on path traversal."""
        full_path = self.validate_path(agent_dir, file_path)
        return Path(full_path).read_text(encoding="utf-8")

    def write_agent_file(self, agent_dir: str, file_path: str, content: str) -> None:
        """Write a file relative to agent_dir. Raises ValueError on path traversal."""
        full_path = self.validate_path(agent_dir, file_path)
        path = Path(full_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_agent_files(self, agent_dir: str) -> list[str]:
        """Return relative paths of all files under agent_dir."""
        root = Path(agent_dir)
        return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]

    def read_agent_files(self, agent_dir: str, exclude_dirs: list[str] | None = None) -> list[dict]:
        """Return [{path, content}] for all text files under agent_dir.

        Skips files in any of the exclude_dirs (relative to agent_dir root).
        Silently skips binary or unreadable files.
        """
        root = Path(agent_dir)
        excluded = set(exclude_dirs or [])
        result = []
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(root)
            if rel.parts[0] in excluded:
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                result.append({"path": str(rel), "content": content})
            except Exception:
                pass
        return result

    def ensure_org_dir(self, base_path: str) -> None:
        """Create {base_path}/agents/ if it does not exist."""
        Path(base_path, "agents").mkdir(parents=True, exist_ok=True)

    def validate_path(self, agent_dir: str, file_path: str) -> str:
        """Resolve file_path relative to agent_dir.

        Raises ValueError if the resolved path escapes agent_dir.
        """
        root = Path(agent_dir).resolve()
        resolved = (root / file_path).resolve()
        if not str(resolved).startswith(str(root) + "/") and resolved != root:
            raise ValueError(f"Path traversal detected: {file_path!r}")
        return str(resolved)
