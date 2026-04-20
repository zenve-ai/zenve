import asyncio

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from zenve_db.models import UserRecord
from zenve_models.run import RunCreate, RunResponse, RunTranscript, SessionResponse
from zenve_models.run_event import RunEventResponse
from zenve_services import (
    get_membership_service,
    get_org_service,
    get_run_dispatch_service,
    get_run_event_service,
    get_run_executor,
    get_run_service,
    get_ws_manager,
)
from zenve_services.run_dispatch import RunDispatchService
from zenve_services.membership import MembershipService
from zenve_services.org import OrgService
from zenve_services.run import RunService
from zenve_services.run_event import RunEventService
from zenve_services.run_executor import RunExecutor
from zenve_services.ws_manager import WebSocketManager
from zenve_utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/orgs/{org_id}/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_run(
    org_id: str,
    body: RunCreate,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
    run_executor: RunExecutor = Depends(get_run_executor),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)

    agent = run_service.get_agent_for_run(org.id, body.agent)

    # Load organization onto agent so build_context can access org_slug
    agent.organization = org

    run = run_service.create_run(
        org_id=org.id,
        agent_id=agent.id,
        trigger="manual",
        adapter_type=body.adapter_type or agent.adapter_type,
        message=body.message,
        session_id=body.session_id,
    )
    ctx = run_executor.build_context(
        agent=agent,
        run_id=run.id,
        message=body.message,
        adapter_type=body.adapter_type,
        adapter_config=body.adapter_config,
        session_id=body.session_id,
    )

    await ws_manager.broadcast(
        org.id,
        {"type": "run.created", "data": RunResponse.model_validate(run).model_dump(mode="json")},
    )
    asyncio.ensure_future(run_executor.execute(run.id, ctx))

    return run


@router.post("/queue", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_run(
    org_id: str,
    body: RunCreate,
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
    dispatch_service: RunDispatchService | None = Depends(get_run_dispatch_service),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
):
    from fastapi import HTTPException

    if dispatch_service is None:
        raise HTTPException(status_code=503, detail="Redis not configured")

    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)

    agent = run_service.get_agent_for_run(org.id, body.agent)
    agent.organization = org

    run = run_service.create_run(
        org_id=org.id,
        agent_id=agent.id,
        trigger="manual",
        adapter_type=body.adapter_type or agent.adapter_type,
        message=body.message,
        session_id=body.session_id,
    )

    await ws_manager.broadcast(
        org.id,
        {"type": "run.created", "data": RunResponse.model_validate(run).model_dump(mode="json")},
    )
    dispatch_service.publish_run(org.slug, run.id)
    return run


@router.get("", response_model=list[RunResponse])
def list_runs(
    org_id: str,
    agent_id: str | None = Query(None),
    run_status: str | None = Query(None, alias="status"),
    trigger: str | None = Query(None),
    session_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return run_service.list_runs(
        org.id,
        agent_id=agent_id,
        status=run_status,
        trigger=trigger,
        session_id=session_id,
        limit=limit,
    )


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


@router.get("/{run_id}/events")
async def stream_run_events(
    org_id: str,
    run_id: str,
    after: str | None = Query(None),
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
    run_event_service: RunEventService = Depends(get_run_event_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    run_service.get_by_id(org.id, run_id)  # 404 if not found

    terminal = {"completed", "failed", "cancelled", "timeout"}

    async def event_generator():
        cursor = after
        poll_interval = 0.5

        while True:
            events = run_event_service.list_by_run(run_id, after_id=cursor, limit=100)
            for event in events:
                data = RunEventResponse.model_validate(event).model_dump_json()
                yield f"id: {event.id}\ndata: {data}\n\n"
                cursor = event.id

            run = run_service.get_by_id(org.id, run_id)
            if run.status in terminal and not events:
                break

            await asyncio.sleep(poll_interval)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


sessions_router = APIRouter(prefix="/api/v1/orgs/{org_id}/sessions", tags=["sessions"])


@sessions_router.get("", response_model=list[SessionResponse])
def list_sessions(
    org_id: str,
    agent_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: UserRecord = Depends(get_current_user),
    org_service: OrgService = Depends(get_org_service),
    membership_service: MembershipService = Depends(get_membership_service),
    run_service: RunService = Depends(get_run_service),
):
    org = org_service.get_by_id_or_slug(org_id)
    membership_service.require_membership(user.id, org.id)
    return run_service.list_sessions(org.id, agent_id=agent_id, limit=limit)
