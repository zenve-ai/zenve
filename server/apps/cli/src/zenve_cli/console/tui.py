from __future__ import annotations

from collections.abc import Callable

from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.widgets import Static

from .formatters import TOOL_FORMATTERS, make_tool_text
from .logo import LOGO
from .theme import AGENT_COLOR, EVENT_BG, OUTPUT_BG, TOOLS_BG


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
        self.replay_events = events or []
        self.run_fn = run_fn

        # Block buffering
        self.block_type: str | None = None
        self.block_lines: list[Text] = []
        self.block_agent: str | None = None
        self.last_agent: str | None = None

        # Run state
        self.run_agents: list[str] = []
        self.agent_states: dict[str, str] = {}
        self.current_action: str = ""
        self.run_id: str = ""
        self.repo: str = ""
        self.snapshot: dict = {}

        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static(LOGO, markup=False, id="logo")
        yield Static("", id="info")
        yield Static("", id="agents")
        with ScrollableContainer(id="log"):
            pass
        yield Static("", id="status")

    def on_mount(self) -> None:
        self.update_status()
        if self.run_fn:
            self.run_worker(self.execute_run, thread=True)
        else:
            for event in self.replay_events:
                self.handle_event(event)
            self.flush_block()
            self.query_one("#log", ScrollableContainer).scroll_end(animate=False)

    # ── Live run worker ───────────────────────────────────────────────────────

    def handle_event_from_thread(self, event: dict) -> None:
        self.call_from_thread(self.handle_event_and_scroll, event)

    def handle_event_and_scroll(self, event: dict) -> None:
        self.handle_event(event)
        self.query_one("#log", ScrollableContainer).scroll_end(animate=False)

    def execute_run(self) -> None:
        assert self.run_fn is not None
        try:
            self.run_fn(self.handle_event_from_thread)
        except Exception as exc:
            self.call_from_thread(
                self.handle_event_and_scroll,
                {"type": "run.failed", "agent": None, "data": {"error": str(exc)}},
            )

    # ── Block helpers ─────────────────────────────────────────────────────────

    def append_log(self, widget: Static) -> None:
        self.query_one("#log", ScrollableContainer).mount(widget)

    def append_panel(
        self,
        content: Text | str,
        *,
        bg: str = EVENT_BG,
        border_style: str | None = None,
        title: str | None = None,
    ) -> None:
        panel = Panel(
            content,
            title=title,
            title_align="right",
            style=f"on {bg}",
            border_style=border_style or bg,
            padding=(0, 1),
        )
        self.append_log(Static(panel))

    def flush_block(self) -> None:
        if not self.block_lines:
            self.block_type = None
            self.block_agent = None
            return

        combined = Text()
        for i, t in enumerate(self.block_lines):
            if i > 0:
                combined.append("\n")
            combined.append_text(t)

        bg = OUTPUT_BG if self.block_type == "output" else TOOLS_BG
        title = f"[{AGENT_COLOR}]{self.block_agent}[/{AGENT_COLOR}]" if self.block_agent else None
        panel = Panel(
            combined,
            title=title,
            title_align="right",
            style=f"on {bg}",
            border_style=bg,
            padding=(0, 1),
        )
        self.append_log(Static(panel))

        self.block_type = None
        self.block_lines = []
        self.block_agent = None

    def add_to_block(self, block_type: str, line: Text) -> None:
        if self.block_type != block_type or self.block_agent != self.last_agent:
            self.flush_block()
            self.block_type = block_type
            self.block_agent = self.last_agent
        self.block_lines.append(line)

    # ── Header agents + status bar ────────────────────────────────────────────

    def update_info(self) -> None:
        t = Text()
        if self.run_id:
            t.append(self.run_id, style="dim")
        if self.repo:
            t.append(" · ", style="dim")
            t.append(self.repo, style="cyan")
        if self.snapshot:
            issues = self.snapshot.get("issues", 0)
            prs = self.snapshot.get("pull_requests", 0)
            branches = self.snapshot.get("branches", 0)
            t.append("   ", style="dim")
            t.append(f"{issues} issues", style="dim")
            t.append(" · ", style="dim")
            t.append(f"{prs} PRs", style="dim")
            t.append(" · ", style="dim")
            t.append(f"{branches} branches", style="dim")
        self.query_one("#info", Static).update(t)

    def update_agents(self) -> None:
        t = Text()
        for i, agent in enumerate(self.run_agents):
            if i > 0:
                t.append("   ")
            state = self.agent_states.get(agent, "pending")
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

    def update_status(self) -> None:
        t = Text()
        if self.current_action:
            t.append(self.current_action, style=f"dim {AGENT_COLOR}")
        t.append("  ctrl+q quit", style="dim")
        self.query_one("#status", Static).update(t)

    # ── Event dispatcher ──────────────────────────────────────────────────────

    def handle_event(self, event: dict) -> None:
        etype = event.get("type", "")
        agent = event.get("agent")
        data = event.get("data", {})

        if etype == "run.started":
            self.run_agents = data.get("agents", [])
            self.agent_states = {a: "pending" for a in self.run_agents}
            self.current_action = ""
            self.run_id = event.get("run_id", "")[:8]
            self.repo = data.get("repo", "")
            self.snapshot = {}
            self.update_info()
            self.update_agents()
            self.update_status()

        elif etype == "snapshot.fetched":
            self.flush_block()
            self.snapshot = data
            self.update_info()

        elif etype == "agent.started":
            self.flush_block()
            self.last_agent = None
            self.current_action = ""
            if agent:
                self.agent_states[agent] = "running"
            self.update_agents()
            self.update_status()

        elif etype == "agent.nothing_to_do":
            self.flush_block()
            if agent:
                self.agent_states[agent] = "done"
            self.current_action = ""
            self.update_agents()
            self.update_status()

        elif etype == "agent.claimed_issue":
            self.flush_block()
            number = data.get("number", "?")
            t = Text("claimed ")
            t.append(f"#{number}", style="bold cyan")
            t.append(f"  {data.get('title', '')}")
            self.append_panel(t, title=f"[{AGENT_COLOR}]{agent}[/{AGENT_COLOR}]" if agent else None)

        elif etype == "agent.claimed_pr":
            self.flush_block()
            number = data.get("number", "?")
            t = Text("claimed PR ")
            t.append(f"#{number}", style="bold cyan")
            t.append(f"  {data.get('title', '')}")
            self.append_panel(t)

        elif etype in ("pipeline.transition", "pipeline.end"):
            self.flush_block()
            if etype == "pipeline.transition":
                msg = f"↳ {data.get('from', '?')} → {data.get('to', '?')}"
            else:
                msg = f"↳ {data.get('from', '?')} → done"
            self.append_panel(Text(msg, style="dim"))

        elif etype == "adapter.output":
            msg = data.get("message", "")
            if not msg:
                return
            if str(msg).splitlines()[0].strip().startswith("Session started:"):
                self.last_agent = None
                return
            if agent and agent != self.last_agent:
                self.last_agent = agent
            self.current_action = "thinking…"
            self.update_status()
            for line in msg.splitlines() or [""]:
                self.add_to_block("output", Text(line))

        elif etype == "adapter.tool_call":
            if agent and agent != self.last_agent:
                self.last_agent = agent
            tool = data.get("tool") or "tool"
            self.current_action = f"▶ {tool}"
            self.update_status()
            formatter = TOOL_FORMATTERS.get(tool)
            line = (
                formatter(data.get("input"))
                if formatter
                else make_tool_text(tool, data.get("input"))
            )
            self.add_to_block("tools", line)

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
                self.flush_block()
                t = Text()
                t.append("usage  ", style="dim yellow")
                t.append(" · ".join(parts), style="dim")
                self.append_panel(t)

        elif etype == "adapter.error":
            self.flush_block()
            if data.get("message"):
                t = Text()
                t.append("error  ", style="red")
                t.append(data["message"])
                self.append_panel(t, border_style="red dim")

        elif etype == "agent.completed":
            self.flush_block()
            if agent:
                self.agent_states[agent] = "done"
            self.current_action = ""
            self.update_agents()
            self.update_status()
            elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
            t = Text()
            t.append("✓ completed", style="bold green")
            if elapsed is not None:
                t.append(f"  {elapsed:.1f}s", style="dim")
            self.append_panel(t, bg=OUTPUT_BG)

        elif etype == "agent.failed":
            self.flush_block()
            if agent:
                self.agent_states[agent] = "failed"
            self.current_action = ""
            self.update_agents()
            self.update_status()
            elapsed = data.get("duration_seconds", data.get("elapsed_seconds"))
            error = data.get("error")
            t = Text()
            t.append("✗ failed", style="bold red")
            if elapsed is not None:
                t.append(f"  {elapsed:.1f}s", style="dim")
            if error:
                t.append(f"  {error}", style="dim red")
            self.append_panel(t, border_style="red dim")

        elif etype == "run.committing":
            self.flush_block()
            self.append_panel(Text("committing…", style="dim"))

        elif etype == "run.completed":
            self.flush_block()

        elif etype == "run.failed":
            self.flush_block()
            body = escape(data.get("error", ""))
            self.append_log(
                Static(
                    Panel(
                        body,
                        title="[bold red]✗  run failed[/bold red]",
                        border_style="red",
                        padding=(0, 1),
                    )
                )
            )
