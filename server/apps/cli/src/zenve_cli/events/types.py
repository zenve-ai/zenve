from __future__ import annotations

RUN_STARTED = "run.started"
RUN_COMMITTING = "run.committing"
RUN_COMPLETED = "run.completed"
RUN_FAILED = "run.failed"

SNAPSHOT_FETCHED = "snapshot.fetched"

AGENT_STARTED = "agent.started"
AGENT_MISCONFIGURED = "agent.misconfigured"
AGENT_NOTHING_TO_DO = "agent.nothing_to_do"
AGENT_CLAIMED_ISSUE = "agent.claimed_issue"
AGENT_CLAIMED_PR = "agent.claimed_pr"
AGENT_COMPLETED = "agent.completed"
AGENT_NEEDS_INPUT = "agent.needs_input"
AGENT_FAILED = "agent.failed"

PIPELINE_TRANSITION = "pipeline.transition"
PIPELINE_END = "pipeline.end"

ADAPTER_OUTPUT = "adapter.output"
ADAPTER_TOOL_CALL = "adapter.tool_call"
ADAPTER_TOOL_RESULT = "adapter.tool_result"
ADAPTER_USAGE = "adapter.usage"
ADAPTER_ERROR = "adapter.error"
