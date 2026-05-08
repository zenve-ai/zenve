from __future__ import annotations

import questionary
from rich.console import Console

console = Console()

WIZARD_STYLE = questionary.Style(
    [
        ("qmark", "fg:#00d4ff bold"),
        ("question", "bold"),
        ("answer", "fg:#00d4ff bold"),
        ("pointer", "fg:#00d4ff bold"),
        ("highlighted", "fg:#00d4ff bold"),
        ("selected", "fg:#00d4ff"),
        ("instruction", "fg:#888888"),
        ("text", ""),
        ("disabled", "fg:#888888 italic"),
    ]
)


def sep() -> None:
    """Print the connecting │ line between wizard steps."""
    console.print("[dim]│[/dim]")
