import importlib.resources

import yaml

from zenve_models.preset import Preset, PresetSummary


class PresetService:
    def list_presets(self) -> list[PresetSummary]:
        presets_pkg = importlib.resources.files("zenve_scaffolding.presets")
        results = []
        for item in presets_pkg.iterdir():
            if not item.name.endswith(".yaml"):
                continue
            data = yaml.safe_load(item.read_text(encoding="utf-8"))
            results.append(
                PresetSummary(
                    name=item.name.removesuffix(".yaml"),
                    description=data.get("description", ""),
                )
            )
        return sorted(results, key=lambda p: p.name)

    def load_preset(self, name: str) -> Preset:
        presets_pkg = importlib.resources.files("zenve_scaffolding.presets")
        target = presets_pkg / f"{name}.yaml"
        if not target.is_file():
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"Preset '{name}' not found")
        data = yaml.safe_load(target.read_text(encoding="utf-8"))
        return Preset(**data)
