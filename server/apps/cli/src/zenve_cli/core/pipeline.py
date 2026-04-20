from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineReport:
    unknown_refs: list[tuple[str, str]]
    cycles: list[list[str]]
    terminals: list[str]

    @property
    def ok(self) -> bool:
        return not self.unknown_refs and not self.cycles


def next_label(pipeline: dict[str, str | None], current: str) -> str | None:
    """Return the label that follows `current`, or None for terminal / unknown."""
    return pipeline.get(current)


def validate_pipeline(pipeline: dict[str, str | None]) -> PipelineReport:
    """Check a pipeline map for unknown label references and cycles.

    - `unknown_refs`: pairs (from, to) where `to` is not a key in the map and not None.
    - `terminals`: labels whose next is None.
    - `cycles`: strongly-connected components of size > 1 (or self-loops).
    """
    keys = set(pipeline.keys())
    unknown_refs: list[tuple[str, str]] = []
    terminals: list[str] = []
    for src, dst in pipeline.items():
        if dst is None:
            terminals.append(src)
            continue
        if dst not in keys:
            unknown_refs.append((src, dst))

    cycles: list[list[str]] = []
    visited: set[str] = set()
    for start in pipeline.keys():
        if start in visited:
            continue
        path: list[str] = []
        index: dict[str, int] = {}
        node: str | None = start
        while node is not None and node not in visited:
            if node in index:
                cycles.append(path[index[node]:] + [node])
                break
            index[node] = len(path)
            path.append(node)
            nxt = pipeline.get(node)
            if nxt is None:
                break
            node = nxt
        visited.update(path)

    return PipelineReport(unknown_refs=unknown_refs, cycles=cycles, terminals=terminals)
