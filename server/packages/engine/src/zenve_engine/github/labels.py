from __future__ import annotations

from zenve_engine.constants import CLAIMED_LABEL, FAILED_LABEL, NEEDS_INPUT_LABEL
from zenve_engine.github.client import GitHubClient, GitHubError


def claim_item(client: GitHubClient, number: int) -> bool:
    """Add zenve:claimed label. Returns True on success, False on GitHubError."""
    try:
        client.add_labels(number, [CLAIMED_LABEL])
    except GitHubError:
        return False
    return True


def unclaim_item(client: GitHubClient, number: int) -> None:
    """Remove zenve:claimed label silently."""
    try:
        client.remove_label(number, CLAIMED_LABEL)
    except GitHubError:
        pass


def transition(
    client: GitHubClient,
    number: int,
    from_label: str,
    to_label: str | None,
) -> None:
    """Post-run label transition (success path).

    - Remove zenve:claimed.
    - Remove current agent label (from_label).
    - Add next pipeline label if not None.
    """
    for lbl in (CLAIMED_LABEL, from_label, FAILED_LABEL, NEEDS_INPUT_LABEL):
        try:
            client.remove_label(number, lbl)
        except GitHubError:
            pass
    if to_label is not None:
        client.add_labels(number, [to_label])
