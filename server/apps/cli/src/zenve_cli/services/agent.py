from zenve_cli.models.agent import AgentCreate
from zenve_cli.services.template import GitHubTemplateService
from zenve_cli.utils.scaffolding import build_settings_json, default_files, slugify


def build_agent_files(
    name: str,
    template_id: str | None,
    template_service: GitHubTemplateService,
) -> tuple[str, dict[str, bytes]]:
    slug = slugify(name)
    if template_id:
        files = template_service.fetch_template_files(template_id)
        manifest = template_service.get_template(template_id)
        slug = manifest.slug or slug
        merged = AgentCreate(
            name=name,
            template=template_id,
            adapter_type=manifest.adapter_type,
            adapter_config=manifest.adapter_config,
            skills=manifest.skills,
            tools=manifest.tools,
            heartbeat_interval_seconds=manifest.heartbeat_interval_seconds,
            mode=manifest.mode,
        )
    else:
        files = default_files()
        merged = AgentCreate(name=name)
    files["settings.json"] = build_settings_json(merged, slug)
    return slug, files
