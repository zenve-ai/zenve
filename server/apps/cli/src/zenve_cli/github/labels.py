from __future__ import annotations

from zenve_cli.github.client import GitHubClient, GitHubError

IN_PROGRESS_LABEL = "in-progress"


def claim_item(
    client: GitHubClient,
    number: int,
    bot_login: str,
) -> bool:
    """Attempt to claim an issue/PR for work.

    Adds `in-progress` label and assigns `bot_login`. Returns True on success,
    False if any step fails (treat as already-claimed by another runner).
    """
    try:
        client.add_labels(number, [IN_PROGRESS_LABEL])
        client.add_assignees(number, [bot_login])
    except GitHubError:
        return False
    return True


def transition(
    client: GitHubClient,
    number: int,
    from_label: str,
    to_label: str | None,
) -> None:
    """Post-run label transition.

    - Remove `in-progress` if present.
    - Remove current `zenve:*` label (`from_label`).
    - Add next pipeline label if not None.
    """
    for lbl in (IN_PROGRESS_LABEL, from_label):
        try:
            client.remove_label(number, lbl)
        except GitHubError:
            pass
    if to_label is not None:
        client.add_labels(number, [to_label])
