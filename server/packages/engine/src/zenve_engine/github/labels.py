from __future__ import annotations

from zenve_engine.constants import CLAIMED_LABEL, FAILED_LABEL, NEEDS_INPUT_LABEL
from zenve_issues import BaseIssueAdapter, IssueUpdate


def claim_item(adapter: BaseIssueAdapter, number: int, current_labels: list[str]) -> bool:
    """Add zenve:claimed label. Returns True on success, False on error."""
    new_labels = [lbl for lbl in current_labels if lbl != CLAIMED_LABEL] + [CLAIMED_LABEL]
    try:
        adapter.update(number, IssueUpdate(labels=new_labels))
    except Exception:
        return False
    return True


def unclaim_item(adapter: BaseIssueAdapter, number: int, current_labels: list[str]) -> None:
    """Remove zenve:claimed label silently."""
    new_labels = [lbl for lbl in current_labels if lbl != CLAIMED_LABEL]
    try:
        adapter.update(number, IssueUpdate(labels=new_labels))
    except Exception:
        pass


def transition(
    adapter: BaseIssueAdapter,
    number: int,
    current_labels: list[str],
    from_label: str,
    to_label: str | None,
) -> None:
    """Post-run label transition (success path).

    - Remove zenve:claimed, current agent label, zenve:failed, zenve:needs-input.
    - Add next pipeline label if not None.
    """
    remove = {CLAIMED_LABEL, from_label, FAILED_LABEL, NEEDS_INPUT_LABEL}
    new_labels = [lbl for lbl in current_labels if lbl not in remove]
    if to_label is not None:
        new_labels.append(to_label)
    try:
        adapter.update(number, IssueUpdate(labels=new_labels))
    except Exception:
        pass
