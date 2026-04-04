from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from zenve.db.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    print("\n" + "=" * 60)
    print("Starting zenve API")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified")

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Application may not function correctly!")

    yield

    engine.dispose()
    print("zenve API shutdown complete")
