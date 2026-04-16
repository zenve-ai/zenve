from fastapi import APIRouter, Depends

from zenve_config.settings import Settings, get_settings
from zenve_db.models import ApiKeyRecord, Organization
from zenve_models.org import OrgMeResponse
from zenve_models.worker import (
    RunCompleteRequest,
    RunCompleteResponse,
    RunContextFile,
    RunContextResponse,
    WorkerRegisterRequest,
    WorkerRegisterResponse,
)
from zenve_services import get_filesystem_service, get_run_service
from zenve_services.api_key_auth import get_current_org
from zenve_services.filesystem import FilesystemService
from zenve_services.run import RunService

router = APIRouter(prefix="/api/v1/worker", tags=["worker"])


@router.get("/org", response_model=OrgMeResponse)
def get_org(
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
):
    org, _ = auth
    return OrgMeResponse.model_validate(org, from_attributes=True)


@router.post("/register", response_model=WorkerRegisterResponse)
def register_worker(
    body: WorkerRegisterRequest,
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
):
    return WorkerRegisterResponse(ok=True)


@router.get("/runs/{run_id}/context", response_model=RunContextResponse)
def get_run_context(
    run_id: str,
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    run_service: RunService = Depends(get_run_service),
    filesystem: FilesystemService = Depends(get_filesystem_service),
    settings: Settings = Depends(get_settings),
):
    org, _ = auth
    run = run_service.get_for_worker(run_id, org.id)
    agent = run.agent

    raw_files = filesystem.read_agent_files(agent.dir_path, exclude_dirs=["runs"])
    files = [RunContextFile(path=f["path"], content=f["content"]) for f in raw_files]

    env_vars = {
        "ZENVE_URL": settings.gateway_url,
        "ZENVE_AGENT_TOKEN": "",  # Chunk 09: short-lived JWT
    }

    return RunContextResponse(
        files=files,
        run_context={
            "agent_id": agent.id,
            "agent_slug": agent.slug,
            "agent_name": agent.name,
            "org_id": org.id,
            "org_slug": org.slug,
        },
        adapter_type=run.adapter_type,
        adapter_config=agent.adapter_config or {},
        message=run.message,
        heartbeat=(run.trigger == "heartbeat"),
        env_vars=env_vars,
    )


@router.post("/runs/{run_id}/complete", response_model=RunCompleteResponse)
def complete_run(
    run_id: str,
    body: RunCompleteRequest,
    auth: tuple[Organization, ApiKeyRecord] = Depends(get_current_org),
    run_service: RunService = Depends(get_run_service),
):
    org, _ = auth
    run = run_service.get_for_worker(run_id, org.id)
    run_service.complete_from_worker(
        run,
        exit_code=body.exit_code,
        stderr=body.stderr,
        token_usage=body.token_usage,
    )
    return RunCompleteResponse(ok=True)
