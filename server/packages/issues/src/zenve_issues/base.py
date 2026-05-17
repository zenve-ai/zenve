from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from zenve_issues.models import (
    Issue,
    IssueAdapterConfigBase,
    IssueCreate,
    IssueListFilter,
    IssueUpdate,
)


class BaseIssueAdapter(ABC):
    """Contract that every issue backend adapter must fulfill.

    An adapter is stateless — it holds no per-call state. A single instance
    is created and reused across all operations. Config is passed into each
    method call.
    """

    adapter_type: ClassVar[str]

    def name(self) -> str:
        return self.__class__.adapter_type

    @classmethod
    @abstractmethod
    def get_default_config(cls) -> IssueAdapterConfigBase: ...

    @classmethod
    @abstractmethod
    def validate_config(cls, raw_config: dict) -> IssueAdapterConfigBase: ...

    @abstractmethod
    def create(self, config: IssueAdapterConfigBase, data: IssueCreate) -> Issue: ...

    @abstractmethod
    def list(
        self,
        config: IssueAdapterConfigBase,
        filters: IssueListFilter | None = None,
    ) -> list[Issue]: ...

    @abstractmethod
    def get(self, config: IssueAdapterConfigBase, issue_id: int) -> Issue: ...

    @abstractmethod
    def update(
        self,
        config: IssueAdapterConfigBase,
        issue_id: int,
        data: IssueUpdate,
    ) -> Issue: ...

    @abstractmethod
    def delete(self, config: IssueAdapterConfigBase, issue_id: int) -> None:
        """Remove the issue from the backend.

        GitHub does not support deleting issues — this closes the issue instead
        (PATCH state=closed). SQLite performs a hard DELETE.
        Must never raise — return None on success.
        """
        ...

    @abstractmethod
    def health_check(self, config: IssueAdapterConfigBase) -> bool:
        """Return True if the backend is reachable. Must never raise."""
        ...
