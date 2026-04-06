from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from zenve.agents.claude_code import ClaudeCodeAdapter
from zenve.agents.registry import AdapterRegistry
from zenve.config.settings import settings
from zenve.db.database import Base, engine
from zenve.services.filesystem import FilesystemService


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

    FilesystemService(settings).seed_default_templates()
    print("Agent templates seeded")

    registry = AdapterRegistry()
    registry.register(ClaudeCodeAdapter())
    app.state.adapter_registry = registry
    print(f"Adapter registry initialized: {registry.known_types()}")

    yield

    engine.dispose()
    print("zenve API shutdown complete")
