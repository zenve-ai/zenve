from fastapi import APIRouter, Depends

from runtime.models.settings import GlobalSettings, GlobalSettingsUpdate
from runtime.services import get_settings_service
from runtime.services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=GlobalSettings)
def get_settings(service: SettingsService = Depends(get_settings_service)):
    return service.get()


@router.patch("", response_model=GlobalSettings)
def update_settings(
    body: GlobalSettingsUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    return service.update(body)
