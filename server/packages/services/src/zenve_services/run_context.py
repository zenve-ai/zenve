from zenve_config.settings import get_settings
from zenve_db.models import Agent
from zenve_models.adapter import RunContext


def build_run_context(
    agent: Agent,
    run_id: str,
    message: str | None = None,
    heartbeat: bool = False,
    agent_token: str = "",
    extra_env: dict | None = None,
) -> RunContext:
    """Build a RunContext from an Agent ORM record.

    Args:
        agent:       Agent ORM instance. agent.organization must be loaded.
        run_id:      UUID string of the Run being executed.
        message:     The user prompt. None for heartbeat runs.
        heartbeat:   True if this is a scheduled heartbeat tick.
        agent_token: Short-lived JWT for agent callbacks (Chunk 09).
        extra_env:   Additional environment variables to inject.

    Returns:
        RunContext ready to be passed into BaseAdapter.execute().
    """
    return RunContext(
        agent_dir=agent.dir_path,
        agent_id=agent.id,
        agent_slug=agent.slug,
        agent_name=agent.name,
        org_id=agent.org_id,
        org_slug=agent.organization.slug,
        run_id=run_id,
        adapter_type=agent.adapter_type,
        adapter_config=agent.adapter_config or {},
        message=message,
        heartbeat=heartbeat,
        gateway_url=get_settings().gateway_url,
        agent_token=agent_token,
        env_vars=extra_env or {},
    )
