from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import ClassVar, Generator

from zenve_issues.base import BaseIssueAdapter
from zenve_issues.models import (
    Issue,
    IssueAdapterConfigBase,
    IssueCreate,
    IssueListFilter,
    IssueNotFoundError,
    IssueUpdate,
    SQLiteIssueConfig,
)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS issues (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    state      TEXT NOT NULL DEFAULT 'open',
    labels     TEXT NOT NULL DEFAULT '[]',
    assignees  TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteIssueAdapter(BaseIssueAdapter):
    adapter_type: ClassVar[str] = "sqlite"

    def __init__(self) -> None:
        # Cached connection for :memory: databases — sqlite3 creates a fresh DB
        # on every sqlite3.connect(":memory:") call, so we reuse one connection.
        self._mem_conn: sqlite3.Connection | None = None

    @classmethod
    def get_default_config(cls) -> SQLiteIssueConfig:
        return SQLiteIssueConfig(db_path=":memory:")

    @classmethod
    def validate_config(cls, raw_config: dict) -> SQLiteIssueConfig:
        return SQLiteIssueConfig.model_validate(raw_config)

    def create(self, config: IssueAdapterConfigBase, data: IssueCreate) -> Issue:
        cfg = SQLiteIssueConfig.model_validate(config.model_dump())
        ts = now_iso()
        with self._connect(cfg) as conn:
            self._ensure_schema(conn)
            cur = conn.execute(
                "INSERT INTO issues (title, body, state, labels, assignees, created_at, updated_at)"
                " VALUES (?, ?, 'open', ?, ?, ?, ?)",
                (data.title, data.body, json.dumps(data.labels), json.dumps(data.assignees), ts, ts),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM issues WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._row_to_issue(row)

    def list(
        self,
        config: IssueAdapterConfigBase,
        filters: IssueListFilter | None = None,
    ) -> list[Issue]:
        cfg = SQLiteIssueConfig.model_validate(config.model_dump())
        f = filters or IssueListFilter()
        with self._connect(cfg) as conn:
            self._ensure_schema(conn)
            query = "SELECT * FROM issues"
            params: list = []
            conditions: list[str] = []
            if f.state != "all":
                conditions.append("state = ?")
                params.append(f.state)
            if f.assignee:
                query = "SELECT DISTINCT issues.* FROM issues, json_each(issues.assignees)"
                conditions.append("json_each.value = ?")
                params.append(f.assignee)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            if f.limit is not None:
                query += f" LIMIT {f.limit}"
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_issue(row) for row in rows]

    def get(self, config: IssueAdapterConfigBase, issue_id: int) -> Issue:
        cfg = SQLiteIssueConfig.model_validate(config.model_dump())
        with self._connect(cfg) as conn:
            self._ensure_schema(conn)
            row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        if row is None:
            raise IssueNotFoundError(issue_id)
        return self._row_to_issue(row)

    def update(
        self,
        config: IssueAdapterConfigBase,
        issue_id: int,
        data: IssueUpdate,
    ) -> Issue:
        cfg = SQLiteIssueConfig.model_validate(config.model_dump())
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return self.get(config, issue_id)
        if "labels" in updates:
            updates["labels"] = json.dumps(updates["labels"])
        if "assignees" in updates:
            updates["assignees"] = json.dumps(updates["assignees"])
        updates["updated_at"] = now_iso()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [issue_id]
        with self._connect(cfg) as conn:
            self._ensure_schema(conn)
            cur = conn.execute(f"UPDATE issues SET {set_clause} WHERE id = ?", values)
            conn.commit()
            if cur.rowcount == 0:
                raise IssueNotFoundError(issue_id)
            row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        return self._row_to_issue(row)

    def delete(self, config: IssueAdapterConfigBase, issue_id: int) -> None:
        cfg = SQLiteIssueConfig.model_validate(config.model_dump())
        with self._connect(cfg) as conn:
            self._ensure_schema(conn)
            cur = conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
            conn.commit()
        if cur.rowcount == 0:
            raise IssueNotFoundError(issue_id)

    def health_check(self, config: IssueAdapterConfigBase) -> bool:
        try:
            cfg = SQLiteIssueConfig.model_validate(config.model_dump())
            with self._connect(cfg) as conn:
                self._ensure_schema(conn)
            return True
        except Exception:
            return False

    @contextmanager
    def _connect(self, cfg: SQLiteIssueConfig) -> Generator[sqlite3.Connection, None, None]:
        if cfg.db_path == ":memory:":
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:")
                self._mem_conn.row_factory = sqlite3.Row
            yield self._mem_conn
        else:
            conn = sqlite3.connect(cfg.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(CREATE_TABLE)

    def _row_to_issue(self, row: sqlite3.Row) -> Issue:
        return Issue(
            id=row["id"],
            title=row["title"],
            body=row["body"],
            state=row["state"],
            labels=json.loads(row["labels"]),
            assignees=json.loads(row["assignees"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
