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
