import importlib.resources
import json
from importlib.resources.abc import Traversable
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from zenve.config.settings import Settings


class FilesystemService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def seed_default_templates(self) -> None:
        """Copy bundled default template set to TEMPLATES_DIR/default/ if absent.

        Idempotent — safe to call on every startup. Never overwrites an
        existing directory so operator customisations are preserved.
        """
        dest = Path(self._settings.templates_dir) / "default"
        if dest.exists():
            return
        dest.mkdir(parents=True, exist_ok=True)
        src: Traversable = importlib.resources.files("zenve.templates") / "default"
        self._copy_traversable(src, dest)

    def _copy_traversable(self, src: Traversable, dest: Path) -> None:
        """Recursively copy a Traversable tree to a real filesystem path."""
        for item in src.iterdir():
            target = dest / item.name
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                self._copy_traversable(item, target)
            else:
                target.write_bytes(item.read_bytes())

    # ------------------------------------------------------------------
    # Scaffolding
    # ------------------------------------------------------------------

    def scaffold_agent_dir(
        self,
        org_slug: str,
        agent_slug: str,
        base_path: str,
        template_vars: dict,
        template_name: str = "default",
    ) -> str:
        """Render templates and create the agent directory structure.

        Returns the absolute path to the created agent directory.
        Raises FileExistsError if the directory already exists.
        """
        agent_dir = Path(base_path) / "agents" / agent_slug
        if agent_dir.exists():
            raise FileExistsError(f"Agent directory already exists: {agent_dir}")

        template_set = Path(self._settings.templates_dir) / template_name
        if not template_set.exists():
            template_set = Path(self._settings.templates_dir) / "default"

        env = Environment(
            loader=FileSystemLoader(str(template_set)),
            keep_trailing_newline=True,
        )

        agent_dir.mkdir(parents=True)
        (agent_dir / "memory").mkdir()
        (agent_dir / "runs").mkdir()

        for template_file in ("SOUL.md.j2", "AGENTS.md.j2", "HEARTBEAT.md.j2", "TOOLS.md.j2"):
            rendered = env.get_template(template_file).render(**template_vars)
            output_name = template_file.removesuffix(".j2")
            (agent_dir / output_name).write_text(rendered, encoding="utf-8")

        self._write_memory_stub(
            agent_dir / "memory" / "long_term.md",
            f"# {template_vars.get('agent_name', agent_slug)} — Long-Term Memory\n\n"
            "This file persists facts, decisions, and context across runs.\n"
            "Update it at the end of each run with anything worth keeping.\n\n---\n\n_No entries yet._\n",
        )
        self._write_memory_stub(
            agent_dir / "memory" / "scratch.md",
            f"# {template_vars.get('agent_name', agent_slug)} — Scratch Memory\n\n"
            "This file holds ephemeral notes within a single run.\n"
            "Clear or summarize it at the end of each run.\n\n---\n\n_Empty._\n",
        )

        return str(agent_dir)

    def _write_memory_stub(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # gateway.json
    # ------------------------------------------------------------------

    def write_gateway_json(self, agent_dir: str, data: dict) -> None:
        """Write or overwrite gateway.json in the agent directory."""
        path = Path(agent_dir) / "gateway.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read_gateway_json(self, agent_dir: str) -> dict:
        """Read and parse gateway.json from the agent directory."""
        path = Path(agent_dir) / "gateway.json"
        return json.loads(path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Generic file operations
    # ------------------------------------------------------------------

    def read_agent_file(self, agent_dir: str, file_path: str) -> str:
        """Read a file relative to agent_dir. Raises ValueError on path traversal."""
        full_path = self._validate_path(agent_dir, file_path)
        return Path(full_path).read_text(encoding="utf-8")

    def write_agent_file(self, agent_dir: str, file_path: str, content: str) -> None:
        """Write a file relative to agent_dir. Raises ValueError on path traversal."""
        full_path = self._validate_path(agent_dir, file_path)
        path = Path(full_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_agent_files(self, agent_dir: str) -> list[str]:
        """Return relative paths of all files under agent_dir."""
        root = Path(agent_dir)
        return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]

    def ensure_org_dir(self, base_path: str) -> None:
        """Create {base_path}/agents/ if it does not exist."""
        Path(base_path, "agents").mkdir(parents=True, exist_ok=True)

    def _validate_path(self, agent_dir: str, file_path: str) -> str:
        """Resolve file_path relative to agent_dir.

        Raises ValueError if the resolved path escapes agent_dir.
        """
        root = Path(agent_dir).resolve()
        resolved = (root / file_path).resolve()
        if not str(resolved).startswith(str(root) + "/") and resolved != root:
            raise ValueError(f"Path traversal detected: {file_path!r}")
        return str(resolved)
