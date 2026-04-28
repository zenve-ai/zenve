from __future__ import annotations

from rich.console import Console

console = Console()

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


def print_event(event: dict) -> None:
    event_type = event.get("type", "")
    agent = event.get("agent")
    data = event.get("data", {})

    if event_type == "run.started":
        agents = data.get("agents", [])
        console.print(f"  agents: {', '.join(agents)}", style="dim")

    elif event_type == "snapshot.fetched":
        issues = data.get("issues", 0)
        prs = data.get("pull_requests", 0)
        branches = data.get("branches", 0)
        console.print(f"  snapshot: {issues} issues · {prs} PRs · {branches} branches", style="dim")

    elif event_type == "agent.started":
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

    elif event_type == "agent.completed":
        elapsed = data.get("elapsed_seconds")
        suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
        console.print(f"  [green]✓ completed[/green]{suffix}")

    elif event_type == "agent.failed":
        elapsed = data.get("elapsed_seconds")
        suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
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
