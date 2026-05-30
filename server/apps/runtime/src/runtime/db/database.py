from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DB_PATH = Path.home() / ".zenve" / "zenve.db"

Base = declarative_base()

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionFactory
    if _engine is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def make_session() -> Session:
    get_engine()
    assert _SessionFactory is not None
    return _SessionFactory()


def get_db():
    db = make_session()
    try:
        yield db
    finally:
        db.close()


def migrate_runs_columns() -> None:
    """Add columns to runs that were added after initial table creation."""
    from sqlalchemy import text
    new_columns = [
        ("agent_name", "TEXT"),
        ("message", "TEXT"),
        ("issue_id", "INTEGER"),
        ("duration_seconds", "REAL"),
        ("exit_code", "INTEGER"),
        ("token_input", "INTEGER"),
        ("token_output", "INTEGER"),
        ("token_cost_usd", "REAL"),
    ]
    engine = get_engine()
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(runs)"))}
        for col_name, col_type in new_columns:
            if col_name not in existing:
                conn.execute(text(f"ALTER TABLE runs ADD COLUMN {col_name} {col_type}"))
        conn.commit()


@contextmanager
def session_scope():
    db = make_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
