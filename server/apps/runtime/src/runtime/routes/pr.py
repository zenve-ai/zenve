from fastapi import APIRouter, Depends

from runtime.models.pr import PRResponse
from runtime.services import get_pr_service
from runtime.services.pr_service import PRService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/pull-requests", tags=["pull-requests"])


@router.get("", response_model=list[PRResponse])
def list_prs(
    workspace_id: str,
    state: str = "open",
    limit: int = 50,
    service: PRService = Depends(get_pr_service),
):
    return service.list_prs(workspace_id, state=state, limit=limit)


@router.get("/{pr_number}", response_model=PRResponse)
def get_pr(
    workspace_id: str,
    pr_number: int,
    service: PRService = Depends(get_pr_service),
):
    return service.get_pr(workspace_id, pr_number)
