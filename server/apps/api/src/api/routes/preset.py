from fastapi import APIRouter, Depends

from zenve_models.preset import Preset, PresetSummary
from zenve_scaffolding import PresetService
from zenve_services import get_preset_service

router = APIRouter(prefix="/api/v1/presets", tags=["presets"])


@router.get("", response_model=list[PresetSummary])
def list_presets(
    service: PresetService = Depends(get_preset_service),
):
    return service.list_presets()


@router.get("/{preset_name}", response_model=Preset)
def get_preset(
    preset_name: str,
    service: PresetService = Depends(get_preset_service),
):
    return service.load_preset(preset_name)
