from __future__ import annotations

from zenve_adapters.base import BaseAdapter
from zenve_adapters.models import RunResult


def extract_failed_reason(outcome: str) -> str | None:
    """Extract the reason from a RUN_FAILED or HEARTBEAT_FAILED signal line."""
    for line in reversed(outcome.strip().splitlines()[-10:]):
        line = line.strip()
        if line.startswith("RUN_FAILED") or line.startswith("HEARTBEAT_FAILED"):
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()
    return None


def determine_run_status(
    result: RunResult,
    adapter_errors: list[str],
) -> tuple[str, str | None]:
    if result.exit_code == 0:
        run_status = BaseAdapter.parse_run_status(result.outcome or "")
    else:
        run_status = "failed"
    status = run_status if run_status in ("completed", "needs_input", "changes_requested") else "failed"
    error_text = result.error
    if status == "failed" and not error_text and result.exit_code == 0 and result.outcome:
        error_text = extract_failed_reason(result.outcome)
    if status == "failed" and not error_text and adapter_errors:
        error_text = adapter_errors[-1]
    if status == "failed" and not error_text:
        error_text = f"Adapter exited with code {result.exit_code}"
    return status, error_text
