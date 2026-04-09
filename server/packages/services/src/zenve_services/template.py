import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from zenve_config.settings import Settings
from zenve_models.template import TemplateManifest, TemplateSummary


class TemplateService:
    def __init__(self, settings: Settings) -> None:
        self._templates_dir = Path(settings.templates_dir)

    def list_templates(self) -> list[TemplateSummary]:
        if not self._templates_dir.exists():
            return []
        results = []
        for child in sorted(self._templates_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest = self._load_manifest(child)
            results.append(TemplateSummary(name=child.name, description=manifest.description))
        return results

    def get_manifest(self, template_name: str) -> TemplateManifest:
        template_dir = self._templates_dir / template_name
        if not template_dir.exists():
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        return self._load_manifest(template_dir)

    def validate_vars(self, template_name: str, template_vars: dict[str, Any] | None) -> None:
        manifest = self.get_manifest(template_name)
        provided = template_vars or {}
        missing = [v.name for v in manifest.variables if v.required and v.name not in provided]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required template variables [{', '.join(missing)}] for template '{template_name}'",
            )

    def resolve_template_name(self, template_name: str) -> str:
        template_dir = self._templates_dir / template_name
        if template_dir.exists():
            return template_name
        return "default"

    def _load_manifest(self, template_dir: Path) -> TemplateManifest:
        manifest_path = template_dir / "manifest.json"
        if not manifest_path.exists():
            return TemplateManifest(name=template_dir.name)
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return TemplateManifest(**data)
