# Chunk 12 — Collaboration Execution Engine

## Goal
Implement the `execute_group_run` Celery task that orchestrates multi-agent collaboration: round-robin execution, prompt building, RESOLVE detection, and routing strategies.

## Depends On
- Chunk 11 (Collaborations Data Model)
- Chunk 05 (Adapter Interface — executes each agent's turn)

## Deliverables

### 1. Routing Strategy — `agents/routing.py`

```python
def get_next_agent(
    members: list[CollaborationMember],
    current_turn: int,
    messages: list[CollaborationMessage],
    strategy: str,
) -> CollaborationMember:
    """Single abstraction point for turn-order logic."""

    if strategy == "round_robin":
        return members[current_turn % len(members)]

    elif strategy == "lead_directed":
        # Parse lead agent's last message for "NEXT: @agent-slug"
        # Fall back to round-robin if not found
        ...

    elif strategy == "llm_orchestrated":
        # Future: lightweight LLM call to pick next speaker
        raise NotImplementedError("llm_orchestrated not yet implemented")

    else:
        return members[current_turn % len(members)]
```

### 2. Collaboration Prompt Builder — `services/collaboration_prompt.py`

```python
def build_collaboration_prompt(
    agent: Agent,
    messages: list[CollaborationMessage],
    collaboration: Collaboration,
    is_lead: bool,
    round_num: int,
) -> str:
    """
    Build the prompt sent to an agent during a collaboration turn.

    Includes:
    - Agent identity (from SOUL.md)
    - Collaboration context (title, members, round)
    - Full message thread so far
    - Instructions (contribute concisely; lead can RESOLVE)
    """

    soul = read_file(Path(agent.dir_path) / "SOUL.md")

    thread = "\n".join([
        f"[{msg.agent_name}]: {msg.content}"
        for msg in messages
    ])

    prompt = f"""You are {agent.name} in a group collaboration.

Your role: {soul}

The team is working on: {collaboration.title}
Round: {round_num}
Members: {', '.join(m.agent_name for m in collaboration.members)}

Conversation so far:
---
{thread}
---

Post your contribution. Be concise — share results, not process."""

    if is_lead:
        prompt += """

You are the lead agent. If the task is complete and you are satisfied with the results, respond with:
RESOLVE: <your final summary>"""

    return prompt
```

### 3. RESOLVE Detection — `services/collaboration_prompt.py`

```python
def is_resolve_signal(content: str) -> bool:
    """Check if the agent's response contains a RESOLVE signal."""
    return content.strip().startswith("RESOLVE:") or "\nRESOLVE:" in content

def extract_resolve_summary(content: str) -> str:
    """Extract the summary after RESOLVE:"""
    for line in content.split("\n"):
        if line.strip().startswith("RESOLVE:"):
            return line.strip()[len("RESOLVE:"):].strip()
    return content
```

### 4. Celery Task — `services/tasks.py`

```python
@celery.task(bind=True)
def execute_group_run(self, collaboration_id: str):
    db = SessionLocal()
    try:
        collab_service = CollaborationService(db)
        run_service = RunService(db)
        agent_service = AgentService(db)

        collab = collab_service.get_by_id(None, UUID(collaboration_id))
        members = collab_service.get_members_ordered(collaboration_id)
        max_turns = collab.max_rounds * len(members)
        turn = 0

        while turn < max_turns:
            messages = collab_service.get_messages(collaboration_id)

            # Get next agent via routing strategy
            member = get_next_agent(members, turn, messages, collab.routing_strategy)
            agent = agent_service.get_by_id(collab.org_id, member.agent_id)
            adapter = adapter_registry.get(agent.adapter_type)
            round_num = turn // len(members)

            collab_service.update(collaboration_id, current_round=round_num)

            # Build prompt with group context
            prompt = build_collaboration_prompt(
                agent=agent,
                messages=messages,
                collaboration=collab,
                is_lead=(member.role == "lead"),
                round_num=round_num,
            )

            # Create sub-run record
            sub_run = run_service.create_run(
                org_id=collab.org_id,
                agent_id=agent.id,
                trigger="collaboration",
                adapter_type=agent.adapter_type,
                message=prompt,
                collaboration_id=UUID(collaboration_id),
            )

            try:
                ctx = build_run_context(agent, sub_run, message=prompt)
                result = adapter.execute(ctx)

                # Extract contribution and save to group thread
                contribution = result.stdout.strip()
                collab_service.add_message(
                    collaboration_id=UUID(collaboration_id),
                    agent_id=agent.id,
                    run_id=sub_run.id,
                    round=round_num,
                    content=contribution,
                    message_type="contribution",
                )

                # Save individual run
                write_transcript(agent, sub_run, result)
                run_service.update(sub_run.id,
                    status="completed",
                    finished_at=utcnow(),
                    token_usage=result.token_usage,
                )

                # Check for RESOLVE from lead
                if member.role == "lead" and is_resolve_signal(contribution):
                    summary = extract_resolve_summary(contribution)
                    collab_service.update(collaboration_id,
                        status="resolved",
                        resolve_summary=summary,
                        finished_at=utcnow(),
                    )
                    return

            except Exception as e:
                collab_service.add_message(
                    collaboration_id=UUID(collaboration_id),
                    agent_id=agent.id,
                    round=round_num,
                    content=f"Agent error: {str(e)}",
                    message_type="error",
                )
                run_service.update(sub_run.id, status="failed", error_summary=str(e))
                # Continue — don't fail the whole collaboration

            turn += 1

        # Max turns without resolution
        collab_service.update(collaboration_id,
            status="max_rounds_reached",
            finished_at=utcnow(),
        )
    finally:
        db.close()
```

## Notes
- The group-run loop is adapter-agnostic — different agents in the same collaboration can use different adapters.
- Only "round_robin" routing is implemented now. "lead_directed" and "llm_orchestrated" are stubs.
- Errors in individual agent turns don't kill the collaboration — an error message is posted and execution continues.
- Each agent's full execution trace (tool calls, reasoning) stays private. Only the stdout contribution is shared.
- The RESOLVE signal is simple string matching. The lead agent must start its response with "RESOLVE:" to end the collaboration.
