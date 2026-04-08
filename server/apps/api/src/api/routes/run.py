import asyncio

from fastapi import APIRouter, Depends, Query, status

from zenve_adapters.registry import AdapterRegistry
from zenve_db.models import UserRecord
from zenve_models.run import RunCreate, RunResponse, RunTranscript
from zenve_services import (
    get_adapter_registry,
    get_membership_service,
    get_org_service,
    get_run_service,
)
from zenve_services.membership import MembershipService
from zenve_services.org import OrgService
from zenve_services.run import RunService
from zenve_services.run_context import build_run_context
from zenve_services.run_executor import execute_run
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/orgs/{org_id}/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_run(
    org_id: str,
    body: RunCreate,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)

    agent = run_service.get_agent_for_run(org.id, body.agent_id)
    run = run_service.create_run(
        org_id=org.id,
        agent_id=agent.id,
        trigger="manual",
        adapter_type=agent.adapter_type,
        message=body.message,
    )

    # Load organization onto agent so build_run_context can access org_slug
    agent.organization = org

    ctx = build_run_context(agent=agent, run_id=run.id, message=body.message)
    asyncio.ensure_future(execute_run(run.id, ctx, adapter_registry))

    return run


@router.get("", response_model=list[RunResponse])
def list_runs(
    org_id: str,
    agent_id: str | None = Query(None),
    run_status: str | None = Query(None, alias="status"),
    trigger: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return run_service.list_runs(org.id, agent_id=agent_id, status=run_status, trigger=trigger, limit=limit)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    org_id: str,
    run_id: str,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return run_service.get_by_id(org.id, run_id)


@router.get("/{run_id}/transcript", response_model=RunTranscript)
def get_transcript(
    org_id: str,
    run_id: str,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
):
    from fastapi import HTTPException

    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    run = run_service.get_by_id(org.id, run_id)
    content = run_service.get_transcript(run)
    if content is None:
        raise HTTPException(status_code=404, detail="Transcript not available yet")
    return RunTranscript(run_id=run_id, content=content)


@router.delete("/{run_id}/cancel", response_model=RunResponse)
def cancel_run(
    org_id: str,
    run_id: str,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    run = run_service.get_by_id(org.id, run_id)
    return run_service.cancel_run(run)
