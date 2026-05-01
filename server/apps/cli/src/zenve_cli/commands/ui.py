from __future__ import annotations

import questionary
from rich.console import Console

console = Console()

WIZARD_STYLE = questionary.Style(
    [
        ("qmark", "fg:#00d4ff bold"),
        ("question", "fg:#ffffff bold"),
        ("answer", "fg:#00d4ff bold"),
        ("pointer", "fg:#00d4ff bold"),
        ("highlighted", "fg:#00d4ff bold"),
        ("selected", "fg:#00d4ff"),
        ("instruction", "fg:#555555"),
        ("text", "fg:#aaaaaa"),
        ("disabled", "fg:#444444 italic"),
    ]
)


def sep() -> None:
    """Print the connecting │ line between wizard steps."""
    console.print("[dim]│[/dim]")
