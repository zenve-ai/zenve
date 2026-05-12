from zenve_cli.models.agent import AgentCreate
from zenve_cli.models.github_template import GitHubTemplateSummary
from zenve_cli.utils.scaffolding import build_settings_json, default_files, slugify


def build_agent_files(
    name: str,
    template: GitHubTemplateSummary | None,
    files: dict[str, bytes],
) -> tuple[str, dict[str, bytes]]:
    slug = slugify(name)
    if template is not None:
        slug = template.slug or slug
        merged = AgentCreate(
            name=name,
            template=template.id,
            adapter_type=template.adapter_type,
            adapter_config=template.adapter_config,
            skills=template.skills,
            tools=template.tools,
            heartbeat_interval_seconds=template.heartbeat_interval_seconds,
            mode=template.mode,
        )
    else:
        files = default_files()
        merged = AgentCreate(name=name)
    files["settings.json"] = build_settings_json(merged, slug)
    return slug, files
