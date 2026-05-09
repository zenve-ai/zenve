from __future__ import annotations


class EngineError(RuntimeError):
    """Base class for engine preflight failures."""


class DirtyTreeError(EngineError):
    """Working tree has uncommitted changes that would be lost or polluted by a run."""


class MissingRemoteBranchError(EngineError):
    """`origin/<branch>` does not exist after `git fetch origin`."""
