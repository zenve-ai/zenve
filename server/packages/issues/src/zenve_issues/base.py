from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from zenve_issues.models import (
    Comment,
    CommentCreate,
    CommentUpdate,
    Issue,
    IssueAdapterConfigBase,
    IssueCreate,
    IssueListFilter,
    IssueUpdate,
)


class BaseIssueAdapter(ABC):
    adapter_type: ClassVar[str]

    def __init__(self, config: IssueAdapterConfigBase) -> None:
        self.config = config

    def name(self) -> str:
        return self.__class__.adapter_type

    @classmethod
    @abstractmethod
    def validate_config(cls, raw_config: dict) -> IssueAdapterConfigBase: ...

    @abstractmethod
    def create(self, data: IssueCreate) -> Issue: ...

    @abstractmethod
    def list(self, filters: IssueListFilter | None = None) -> list[Issue]: ...

    @abstractmethod
    def get(self, issue_id: int) -> Issue: ...

    @abstractmethod
    def update(self, issue_id: int, data: IssueUpdate) -> Issue: ...

    @abstractmethod
    def delete(self, issue_id: int) -> None:
        """Remove the issue from the backend.

        GitHub does not support deleting issues — this closes the issue instead
        (PATCH state=closed). SQLite performs a hard DELETE.
        Must never raise — return None on success.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the backend is reachable. Must never raise."""
        ...

    @abstractmethod
    def add_comment(self, issue_id: int, data: CommentCreate) -> Comment: ...

    @abstractmethod
    def list_comments(self, issue_id: int) -> list[Comment]: ...

    @abstractmethod
    def get_comment(self, comment_id: int) -> Comment: ...

    @abstractmethod
    def update_comment(self, comment_id: int, data: CommentUpdate) -> Comment: ...

    @abstractmethod
    def delete_comment(self, comment_id: int) -> None: ...

    @abstractmethod
    def list_labels(self) -> list[str]: ...
