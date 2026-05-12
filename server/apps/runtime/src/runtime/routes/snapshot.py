from fastapi import APIRouter, Depends

from runtime.models.snapshot import SnapshotResponse
from runtime.services import get_snapshot_service
from runtime.services.snapshot_service import SnapshotService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}", tags=["snapshot"])


@router.post("/snapshot", response_model=SnapshotResponse)
def take_snapshot(
    workspace_id: str,
    service: SnapshotService = Depends(get_snapshot_service),
):
    return service.take(workspace_id)
