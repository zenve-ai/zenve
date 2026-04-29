from __future__ import annotations

import json
from collections.abc import Callable

from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.widgets import Static

# ── Theme ────────────────────────────────────────────────────────────────────
OUTPUT_BG = "grey15"
TOOLS_BG = "grey11"
AGENT_COLOR = "grey50"

LOGO = """███████╗ ███████╗ ███╗   ██╗ ██╗   ██╗ ███████╗
╚══███╔╝ ██╔════╝ ████╗  ██║ ██║   ██║ ██╔════╝
  ███╔╝  █████╗   ██╔██╗ ██║ ██║   ██║ █████╗
 ███╔╝   ██╔══╝   ██║╚██╗██║ ╚██╗ ██╔╝ ██╔══╝
███████╗ ███████╗ ██║ ╚████║  ╚████╔╝  ███████╗
╚══════╝ ╚══════╝ ╚═╝  ╚═══╝   ╚═══╝   ╚══════╝"""


# ── Tool formatter registry ──────────────────────────────────────────────────

TOOL_FORMATTERS: dict[str, Callable[[dict | None], Text]] = {}


def format_tool_args(payload: dict, max_str_len: int = 60) -> str:
    parts: list[str] = []
    for k, v in payload.items():
        if isinstance(v, str):
            truncated = v if len(v) <= max_str_len else v[: max_str_len - 3] + "..."
            parts.append(f'{k}="{truncated}"')
        elif isinstance(v, (int, float, bool)):
            parts.append(f"{k}={v}")
        else:
            s = json.dumps(v, separators=(",", ":"))
            if len(s) > max_str_len:
                s = s[: max_str_len - 3] + "..."
            parts.append(f"{k}={s}")
    return "  ".join(parts)


def make_tool_text(tool: str, payload: dict | None) -> Text:
    t = Text()
    t.append("▶ ", style="cyan")
    t.append(tool, style="bold")
    if payload:
        t.append("  ")
        t.append(escape(format_tool_args(payload)), style="dim")
    return t


def fmt_read(payload: dict | None) -> Text:
    p = payload or {}
    path = p.get("filePath") or p.get("path", "")
    t = Text()
    t.append("▶ ", style="cyan")
    t.append("read", style="bold")
    t.append("  ")
    t.append(str(path), style="dim")
    return t


def fmt_bash(payload: dict | None) -> Text:
    cmd = (payload or {}).get("command", "")
    if len(cmd) > 80:
        cmd = cmd[:77] + "..."
    t = Text()
    t.append("▶ ", style="cyan")
    t.append("bash", style="bold")
    t.append("  ")
    t.append(cmd, style="dim")
    return t


TOOL_FORMATTERS["read"] = fmt_read
TOOL_FORMATTERS["bash"] = fmt_bash


# ── TUI App ──────────────────────────────────────────────────────────────────


class ZenveTUI(App):
    BINDINGS = [Binding("ctrl+q", "quit", "quit")]

    CSS = """
    Screen {
        layout: vertical;
    }

    #logo {
        padding: 1 2 0 2;
        color: cyan;
    }

    #info {
        padding: 0 2 0 2;
        color: #808080;
    }

    #agents {
        padding: 0 2 1 2;
        border-bottom: solid #3a3a3a;
    }

    #log {
        height: 1fr;
        overflow-y: auto;
        padding: 1 2;
    }

    #status {
        dock: bottom;
        height: 1;
        background: $panel;
        padding: 0 2;
    }
    """

    def __init__(
        self,
        events: list[dict] | None = None,
        run_fn: Callable[[Callable[[dict], None]], None] | None = None,
    ) -> None:
        self._events = events or []
        self._run_fn = run_fn

        # Block buffering
        self._block_type: str | None = None
        self._block_lines: list[Text] = []
        self._block_agent: str | None = None
        self._last_agent: str | None = None

        # Run state
        self._run_agents: list[str] = []
        self._agent_states: dict[str, str] = {}
        self._current_action: str = ""
        self._run_id: str = ""
        self._repo: str = ""
        self._snapshot: dict = {}

        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static(LOGO, markup=False, id="logo")
        yield Static("", id="info")
        yield Static("", id="agents")
        with ScrollableContainer(id="log"):
            pass
        yield Static("", id="status")

    def on_mount(self) -> None:
        self._update_status()
        if self._run_fn:
            self.run_worker(self._execute_run, thread=True)
        else:
            for event in self._events:
                self._dispatch(event)
            self._flush_block()
            self.query_one("#log", ScrollableContainer).scroll_end(animate=False)

    # ── Live run worker ───────────────────────────────────────────────────────

    def _dispatch_from_thread(self, event: dict) -> None:
        """Called from the worker thread to safely dispatch an event into the TUI."""
        self.call_from_thread(self._dispatch_and_scroll, event)

    def _dispatch_and_scroll(self, event: dict) -> None:
        self._dispatch(event)
        self.query_one("#log", ScrollableContainer).scroll_end(animate=False)

    def _execute_run(self) -> None:
        """Thread worker: runs the agent pipeline and feeds events into the TUI."""
        assert self._run_fn is not None
        try:
            self._run_fn(self._dispatch_from_thread)
        except Exception as exc:
            self.call_from_thread(
                self._dispatch_and_scroll,
                {"type": "run.failed", "agent": None, "data": {"error": str(exc)}},
            )

    # ── Block helpers ─────────────────────────────────────────────────────────

    def _log(self, widget: Static) -> None:
        self.query_one("#log", ScrollableContainer).mount(widget)

    def _flush_block(self) -> None:
        if not self._block_lines:
            self._block_type = None
            self._block_agent = None
            return

        combined = Text()
        for i, t in enumerate(self._block_lines):
            if i > 0:
                combined.append("\n")
            combined.append_text(t)

        bg = OUTPUT_BG if self._block_type == "output" else TOOLS_BG
        title = f"[{AGENT_COLOR}]{self._block_agent}[/{AGENT_COLOR}]" if self._block_agent else None
        panel = Panel(
            combined,
            title=title,
            title_align="right",
            style=f"on {bg}",
            border_style=bg,
            padding=(0, 1),
        )
        self._log(Static(panel))

        self._block_type = None
        self._block_lines = []
        self._block_agent = None

    def _add(self, block_type: str, line: Text) -> None:
        if self._block_type != block_type or self._block_agent != self._last_agent:
            self._flush_block()
            self._block_type = block_type
            self._block_agent = self._last_agent
        self._block_lines.append(line)

    # ── Header agents + status bar ────────────────────────────────────────────

    def _update_info(self) -> None:
        t = Text()
        if self._run_id:
            t.append(self._run_id, style="dim")
        if self._repo:
            t.append(" · ", style="dim")
            t.append(self._repo, style="cyan")
        if self._snapshot:
            issues = self._snapshot.get("issues", 0)
            prs = self._snapshot.get("pull_requests", 0)
            branches = self._snapshot.get("branches", 0)
            t.append("   ", style="dim")
            t.append(f"{issues} issues", style="dim")
            t.append(" · ", style="dim")
            t.append(f"{prs} PRs", style="dim")
            t.append(" · ", style="dim")
            t.append(f"{branches} branches", style="dim")
        self.query_one("#info", Static).update(t)

    def _update_agents(self) -> None:
        t = Text()
        for i, agent in enumerate(self._run_agents):
            if i > 0:
                t.append("   ")
            state = self._agent_states.get(agent, "pending")
            if state == "running":
                t.append("● ", style="bold cyan")
                t.append(agent, style="bold")
            elif state == "done":
                t.append("✓ ", style="dim green")
                t.append(agent, style="dim")
            elif state == "failed":
                t.append("✗ ", style="dim red")
                t.append(agent, style="dim")
            else:
                t.append("○ ", style="dim")
                t.append(agent, style="dim")
        self.query_one("#agents", Static).update(t)

    def _update_status(self) -> None:
        t = Text()
        if self._current_action:
            t.append(self._current_action, style=f"dim {AGENT_COLOR}")
        t.append("  ctrl+q quit", style="dim")
        self.query_one("#status", Static).update(t)

    # ── Event dispatcher ──────────────────────────────────────────────────────

    def _dispatch(self, event: dict) -> None:
        etype = event.get("type", "")
        agent = event.get("agent")
        data = event.get("data", {})

        if etype == "run.started":
            self._run_agents = data.get("agents", [])
            self._agent_states = {a: "pending" for a in self._run_agents}
            self._current_action = ""
            self._run_id = event.get("run_id", "")[:8]
            self._repo = data.get("repo", "")
            self._snapshot = {}
            self._update_info()
            self._update_agents()
            self._update_status()

        elif etype == "snapshot.fetched":
            self._flush_block()
            self._snapshot = data
            self._update_info()

        elif etype == "agent.started":
            self._flush_block()
            self._last_agent = None
            self._current_action = ""
            if agent:
                self._agent_states[agent] = "running"
            self._update_agents()
            self._update_status()
            self._log(Static(Rule(f"[bold]{agent}[/bold]", align="left", style="dim")))

        elif etype == "agent.nothing_to_do":
            self._flush_block()
            if agent:
                self._agent_states[agent] = "done"
            self._current_action = ""
            self._update_agents()
            self._update_status()
            self._log(Static(Text("  nothing to do", style="dim")))

        elif etype == "agent.claimed_issue":
            self._flush_block()
            number = data.get("number", "?")
            t = Text("  claimed ")
            t.append(f"#{number}", style="bold cyan")
            t.append(f"  {data.get('title', '')}")
            self._log(Static(t))

        elif etype == "agent.claimed_pr":
            self._flush_block()
            number = data.get("number", "?")
            t = Text("  claimed PR ")
            t.append(f"#{number}", style="bold cyan")
            t.append(f"  {data.get('title', '')}")
            self._log(Static(t))

        elif etype in ("pipeline.transition", "pipeline.end"):
            self._flush_block()
            if etype == "pipeline.transition":
                msg = f"  ↳ {data.get('from', '?')} → {data.get('to', '?')}"
            else:
                msg = f"  ↳ {data.get('from', '?')} → done"
            self._log(Static(Text(msg, style="dim")))

        elif etype == "adapter.output":
            msg = data.get("message", "")
            if not msg:
                return
            if str(msg).splitlines()[0].strip().startswith("Session started:"):
                self._last_agent = None
                return
            if agent and agent != self._last_agent:
                self._last_agent = agent
            self._current_action = "thinking…"
            self._update_status()
            for line in msg.splitlines() or [""]:
                self._add("output", Text(line))

        elif etype == "adapter.tool_call":
            if agent and agent != self._last_agent:
                self._last_agent = agent
            tool = data.get("tool") or "tool"
            self._current_action = f"▶ {tool}"
            self._update_status()
            formatter = TOOL_FORMATTERS.get(tool)
            line = (
                formatter(data.get("input"))
                if formatter
                else make_tool_text(tool, data.get("input"))
            )
            self._add("tools", line)

        elif etype == "adapter.usage":
            parts: list[str] = []
            if data.get("input_tokens") is not None:
                parts.append(f"↑ {data['input_tokens']:,}")
            if data.get("output_tokens") is not None:
                parts.append(f"↓ {data['output_tokens']:,}")
            if data.get("reasoning_tokens") is not None:
                parts.append(f"think {data['reasoning_tokens']:,}")
            if data.get("cache_read_input_tokens") is not None:
                parts.append(f"cache {data['cache_read_input_tokens']:,}")
            if data.get("cost_usd") is not None:
                parts.append(f"${data['cost_usd']:.4f}")
            if parts:
                self._flush_block()
                t = Text("  ")
                t.append("usage  ", style="dim yellow")
                t.append(" · ".join(parts), style="dim")
                self._log(Static(t))

        elif etype == "adapter.error":
            self._flush_block()
            if data.get("message"):
                t = Text("  ")
                t.append("error  ", style="red")
                t.append(data["message"])
                self._log(Static(t))

        elif etype == "agent.completed":
            self._flush_block()
            if agent:
                self._agent_states[agent] = "done"
            self._current_action = ""
            self._update_agents()
            self._update_status()
            elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
            t = Text("  ")
            t.append("✓ completed", style="bold green")
            if elapsed is not None:
                t.append(f"  {elapsed:.1f}s", style="dim")
            self._log(Static(t))

        elif etype == "agent.failed":
            self._flush_block()
            if agent:
                self._agent_states[agent] = "failed"
            self._current_action = ""
            self._update_agents()
            self._update_status()
            elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
            error = data.get("error")
            t = Text("  ")
            t.append("✗ failed", style="bold red")
            if elapsed is not None:
                t.append(f"  {elapsed:.1f}s", style="dim")
            if error:
                t.append(f"  {error}", style="dim red")
            self._log(Static(t))

        elif etype == "run.committing":
            self._flush_block()
            self._log(Static(Text("  committing…", style="dim")))

        elif etype == "run.completed":
            self._flush_block()
            # agents_count = data.get("agents")
            # subtitle = f"[dim]{agents_count} agent(s)[/dim]" if agents_count is not None else ""
            # self._log(Static(Panel("", title="[bold green]✓  run complete[/bold green]",
            #                        subtitle=subtitle, border_style="green", padding=(0, 0))))

        elif etype == "run.failed":
            self._flush_block()
            body = escape(data.get("error", ""))
            self._log(
                Static(
                    Panel(
                        body,
                        title="[bold red]✗  run failed[/bold red]",
                        border_style="red",
                        padding=(0, 1),
                    )
                )
            )


# ── Real-time event printer ───────────────────────────────────────────────────

from rich.console import Console as _Console  # noqa: E402

_console = _Console()


def print_logo() -> None:
    _console.print(Text(LOGO, style="bold cyan"))


def print_event(event: dict) -> None:
    etype = event.get("type", "")
    agent = event.get("agent")
    data = event.get("data", {})

    if etype == "run.started":
        repo = data.get("repo", "")
        run_id = event.get("run_id", "")[:8]
        agents = "  ".join(data.get("agents", []))
        title = f"[dim]{run_id}[/dim]"
        if repo:
            title += f" [dim]·[/dim] [cyan]{repo}[/cyan]"
        _console.print(
            Panel(agents, title=title, title_align="left", border_style="dim cyan", padding=(0, 1))
        )

    elif etype == "snapshot.fetched":
        issues, prs, branches = (
            data.get("issues", 0),
            data.get("pull_requests", 0),
            data.get("branches", 0),
        )
        _console.print(
            Text(f"  snapshot  {issues} issues · {prs} PRs · {branches} branches", style="dim")
        )

    elif etype == "agent.started":
        _console.print(Rule(f"[bold]{agent}[/bold]", align="left", style="dim"))

    elif etype == "agent.nothing_to_do":
        _console.print(Text("  nothing to do", style="dim"))

    elif etype == "agent.claimed_issue":
        number = data.get("number", "?")
        t = Text("  claimed ")
        t.append(f"#{number}", style="bold cyan")
        t.append(f"  {data.get('title', '')}")
        _console.print(t)

    elif etype == "agent.claimed_pr":
        number = data.get("number", "?")
        t = Text("  claimed PR ")
        t.append(f"#{number}", style="bold cyan")
        t.append(f"  {data.get('title', '')}")
        _console.print(t)

    elif etype in ("pipeline.transition", "pipeline.end"):
        if etype == "pipeline.transition":
            msg = f"  ↳ {data.get('from', '?')} → {data.get('to', '?')}"
        else:
            msg = f"  ↳ {data.get('from', '?')} → done"
        _console.print(Text(msg, style="dim"))

    elif etype == "adapter.output":
        msg = data.get("message", "")
        if msg and not str(msg).splitlines()[0].strip().startswith("Session started:"):
            _console.print(Text(msg), end="")

    elif etype == "adapter.tool_call":
        tool = data.get("tool") or "tool"
        formatter = TOOL_FORMATTERS.get(tool)
        line = (
            formatter(data.get("input")) if formatter else make_tool_text(tool, data.get("input"))
        )
        _console.print(line)

    elif etype == "adapter.usage":
        parts: list[str] = []
        if data.get("input_tokens") is not None:
            parts.append(f"↑ {data['input_tokens']:,}")
        if data.get("output_tokens") is not None:
            parts.append(f"↓ {data['output_tokens']:,}")
        if data.get("cost_usd") is not None:
            parts.append(f"${data['cost_usd']:.4f}")
        if parts:
            t = Text("  ")
            t.append("usage  ", style="dim yellow")
            t.append(" · ".join(parts), style="dim")
            _console.print(t)

    elif etype == "adapter.error":
        if data.get("message"):
            t = Text("  ")
            t.append("error  ", style="red")
            t.append(data["message"])
            _console.print(t)

    elif etype == "agent.completed":
        elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
        t = Text("  ")
        t.append("✓ completed", style="bold green")
        if elapsed is not None:
            t.append(f"  {elapsed:.1f}s", style="dim")
        _console.print(t)

    elif etype == "agent.failed":
        elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
        error = data.get("error")
        t = Text("  ")
        t.append("✗ failed", style="bold red")
        if elapsed is not None:
            t.append(f"  {elapsed:.1f}s", style="dim")
        if error:
            t.append(f"  {error}", style="dim red")
        _console.print(t)

    elif etype == "run.committing":
        _console.print(Text("  committing…", style="dim"))

    elif etype == "run.completed":
        agents_count = data.get("agents")
        subtitle = f"[dim]{agents_count} agent(s)[/dim]" if agents_count is not None else ""
        _console.print(
            Panel(
                "",
                title="[bold green]✓  run complete[/bold green]",
                subtitle=subtitle,
                border_style="green",
                padding=(0, 0),
            )
        )

    elif etype == "run.failed":
        body = escape(data.get("error", ""))
        _console.print(
            Panel(
                body, title="[bold red]✗  run failed[/bold red]", border_style="red", padding=(0, 1)
            )
        )
