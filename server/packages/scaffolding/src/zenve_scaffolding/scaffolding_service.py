import importlib.resources
from importlib.resources.abc import Traversable
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from zenve_config.settings import Settings


class ScaffoldingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def seed_default_templates(self) -> None:
        """Copy bundled default template set to TEMPLATES_DIR/default/ if absent.

        Idempotent — safe to call on every startup. Never overwrites an
        existing directory so operator customisations are preserved.
        manifest.json is always synced since it is package metadata, not
        user-customisable content.
        """
        src: Traversable = importlib.resources.files("zenve_scaffolding.templates") / "default"
        dest = Path(self.settings.templates_dir) / "default"
        if not dest.exists():
            dest.mkdir(parents=True, exist_ok=True)
            self.copy_traversable(src, dest)
            return
        bundled_manifest = src / "manifest.json"
        if bundled_manifest.is_file():
            (dest / "manifest.json").write_bytes(bundled_manifest.read_bytes())

    def copy_traversable(self, src: Traversable, dest: Path) -> None:
        """Recursively copy a Traversable tree to a real filesystem path."""
        for item in src.iterdir():
            target = dest / item.name
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                self.copy_traversable(item, target)
            else:
                target.write_bytes(item.read_bytes())

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

        template_set = Path(self.settings.templates_dir) / template_name
        if not template_set.exists():
            template_set = Path(self.settings.templates_dir) / "default"

        env = Environment(
            loader=FileSystemLoader(str(template_set)),
            keep_trailing_newline=True,
        )

        agent_dir.mkdir(parents=True)
        (agent_dir / "memory").mkdir()
        (agent_dir / "runs").mkdir()

        for template_file in (
            "SOUL.md.j2",
            "AGENTS.md.j2",
            "RUN.md.j2",
            "HEARTBEAT.md.j2",
        ):
            rendered = env.get_template(template_file).render(**template_vars)
            output_name = template_file.removesuffix(".j2")
            (agent_dir / output_name).write_text(rendered, encoding="utf-8")

        self.write_memory_stub(
            agent_dir / "memory" / "long_term.md",
            f"# {agent_slug} — Long-Term Memory\n\n"
            "This file persists facts, decisions, and context across runs.\n"
            "Update it at the end of each run with anything worth keeping.\n\n---\n\n_No entries yet._\n",
        )
        self.write_memory_stub(
            agent_dir / "memory" / "scratch.md",
            f"# {agent_slug} — Scratch Memory\n\n"
            "This file holds ephemeral notes within a single run.\n"
            "Clear or summarize it at the end of each run.\n\n---\n\n_Empty._\n",
        )

        return str(agent_dir)

    def write_memory_stub(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
