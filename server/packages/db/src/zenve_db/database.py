from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from zenve_config.settings import settings


def create_sqlite_engine(path: str | None = None):
    if path is None:
        path = settings.sqlite_database_url
    if not path:
        raise ValueError("SQLITE_DATABASE_URL is not set.")
    return create_engine(f"sqlite:///{path}")


def create_postgres_engine(connection_string: str | None = None):
    if connection_string is None:
        connection_string = settings.pg_database_url
    if not connection_string:
        raise ValueError("PG_DATABASE_URL is not set.")
    return create_engine(connection_string)


Base = declarative_base()

engine = create_sqlite_engine()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
