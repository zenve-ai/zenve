from __future__ import annotations

import json

from rich.console import Console
from rich.text import Text

console = Console()
_last_adapter_agent: str | None = None

LOGO = """███████╗ ███████╗ ███╗   ██╗ ██╗   ██╗ ███████╗
╚══███╔╝ ██╔════╝ ████╗  ██║ ██║   ██║ ██╔════╝
  ███╔╝  █████╗   ██╔██╗ ██║ ██║   ██║ █████╗
 ███╔╝   ██╔══╝   ██║╚██╗██║ ╚██╗ ██╔╝ ██╔══╝
███████╗ ███████╗ ██║ ╚████║  ╚████╔╝  ███████╗
╚══════╝ ╚══════╝ ╚═╝  ╚═══╝   ╚═══╝   ╚══════╝"""


def print_logo() -> None:
    console.print()
    console.print(LOGO, style="bold cyan")
    console.print()


def _print_adapter_agent(agent: str | None) -> None:
    global _last_adapter_agent
    if not agent or agent == _last_adapter_agent:
        return
    console.print(f"  [dim][{agent}][/dim]")
    _last_adapter_agent = agent


def _print_adapter_output(message: str | None) -> None:
    if not message:
        return
    for line in str(message).splitlines() or [""]:
        console.print(f"  [white]│[/white] {line}")


def _is_session_started(message: str | None) -> bool:
    if not message:
        return False
    first_line = str(message).splitlines()[0].strip()
    return first_line.startswith("Session started:")


def _print_adapter_tool_call(tool: str | None, payload: dict | None) -> None:
    label = tool or "tool"
    console.print(f"  [cyan]●[/cyan] [bold]{label}[/bold]", end="")
    if payload:
        rendered = json.dumps(payload, sort_keys=True)
        console.print(f" [dim]{rendered}[/dim]")
    else:
        console.print()


def _print_adapter_usage(data: dict) -> None:
    parts: list[str] = []

    if data.get("input_tokens") is not None:
        parts.append(f"in {data['input_tokens']:,}")
    if data.get("output_tokens") is not None:
        parts.append(f"out {data['output_tokens']:,}")
    if data.get("reasoning_tokens") is not None:
        parts.append(f"reason {data['reasoning_tokens']:,}")
    if data.get("cache_read_input_tokens") is not None:
        parts.append(f"cache {data['cache_read_input_tokens']:,}")
    if data.get("cost_usd") is not None:
        parts.append(f"cost ${data['cost_usd']:.4f}")

    if not parts:
        return

    usage_line = Text("  usage ", style="yellow")
    usage_line.append("·", style="dim")
    usage_line.append(" " + " · ".join(parts), style="dim")
    console.print(usage_line)


def print_event(event: dict) -> None:
    event_type = event.get("type", "")
    agent = event.get("agent")
    data = event.get("data", {})

    global _last_adapter_agent

    if event_type == "run.started":
        _last_adapter_agent = None
        agents = data.get("agents", [])
        console.print(f"  agents: {', '.join(agents)}", style="dim")

    elif event_type == "snapshot.fetched":
        issues = data.get("issues", 0)
        prs = data.get("pull_requests", 0)
        branches = data.get("branches", 0)
        console.print(f"  snapshot: {issues} issues · {prs} PRs · {branches} branches", style="dim")

    elif event_type == "agent.started":
        _last_adapter_agent = None
        console.print()
        console.print(f"[bold cyan]◆[/bold cyan] [bold white]{agent}[/bold white]")

    elif event_type == "agent.nothing_to_do":
        console.print("  [dim]nothing to do[/dim]")

    elif event_type == "agent.claimed_issue":
        number = data.get("number", "?")
        title = data.get("title", "")
        console.print(f"  claimed issue [cyan]#{number}[/cyan]: {title}")

    elif event_type == "agent.claimed_pr":
        number = data.get("number", "?")
        title = data.get("title", "")
        console.print(f"  claimed PR [cyan]#{number}[/cyan]: {title}")

    elif event_type == "pipeline.transition":
        from_label = data.get("from_label", "?")
        to_label = data.get("to_label", "?")
        console.print(f"  pipeline: {from_label} → {to_label}", style="dim")

    elif event_type == "pipeline.end":
        from_label = data.get("from_label", "?")
        console.print(f"  pipeline: {from_label} → [dim]done[/dim]")

    elif event_type == "adapter.output":
        if _is_session_started(data.get("message")):
            _last_adapter_agent = None
            console.print()
        _print_adapter_agent(agent)
        _print_adapter_output(data.get("message"))

    elif event_type == "adapter.tool_call":
        _print_adapter_agent(agent)
        _print_adapter_tool_call(data.get("tool"), data.get("input"))

    elif event_type == "adapter.usage":
        _print_adapter_agent(agent)
        _print_adapter_usage(data)

    elif event_type == "adapter.error":
        _print_adapter_agent(agent)
        message = data.get("message")
        if message:
            console.print(f"  [red]error[/red]: {message}")

    elif event_type == "agent.completed":
        elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
        suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
        console.print(f"  [green]✓ completed[/green]{suffix}")

    elif event_type == "agent.failed":
        elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
        error = data.get("error")
        suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
        if error:
            console.print(f"  [red]✗ failed[/red]{suffix}: {error}")
        else:
            console.print(f"  [red]✗ failed[/red]{suffix}")

    elif event_type == "run.committing":
        console.print("[dim]  committing...[/dim]")

    elif event_type == "run.completed":
        agents_count = data.get("agents")
        suffix = f" ({agents_count} agents)" if agents_count is not None else ""
        console.print(f"[green]✓ run complete[/green]{suffix}")

    elif event_type == "run.failed":
        error = data.get("error", "")
        console.print(f"[red]✗ run failed[/red]: {error}" if error else "[red]✗ run failed[/red]")
