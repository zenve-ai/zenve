from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from zenve_config.settings import get_settings


def create_sqlite_engine(path: str | None = None):
    if path is None:
        path = get_settings().sqlite_database_url
    if not path:
        raise ValueError("SQLITE_DATABASE_URL is not set.")
    return create_engine(f"sqlite:///{path}")


def create_postgres_engine(connection_string: str | None = None):
    if connection_string is None:
        connection_string = get_settings().pg_database_url
    if not connection_string:
        raise ValueError("PG_DATABASE_URL is not set.")
    return create_engine(connection_string)


Base = declarative_base()

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionFactory
    if _engine is None:
        _engine = create_postgres_engine()
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
