"""Replay an events.log file in the Zenve TUI.

Usage:
    uv run python examples/replay_events.py [path/to/events.log]

Defaults to server/events.log when no path is given.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps/cli/src"))

from zenve_cli.console import ZenveTUI

log_path = (
    Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "examples/events.log"
)

with log_path.open() as f:
    events = [json.loads(line) for line in f if line.strip()]

ZenveTUI(events).run()
