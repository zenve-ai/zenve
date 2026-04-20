from __future__ import annotations

RUN_STARTED = "run.started"
RUN_COMMITTING = "run.committing"
RUN_COMPLETED = "run.completed"
RUN_FAILED = "run.failed"

SNAPSHOT_FETCHED = "snapshot.fetched"

AGENT_STARTED = "agent.started"
AGENT_NOTHING_TO_DO = "agent.nothing_to_do"
AGENT_CLAIMED_ISSUE = "agent.claimed_issue"
AGENT_CLAIMED_PR = "agent.claimed_pr"
AGENT_COMPLETED = "agent.completed"
AGENT_FAILED = "agent.failed"

PIPELINE_TRANSITION = "pipeline.transition"
PIPELINE_END = "pipeline.end"
