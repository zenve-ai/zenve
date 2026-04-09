import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_adapters.registry import AdapterRegistry
from zenve_config.settings import settings
from zenve_db.database import Base, engine
from zenve_services.filesystem import FilesystemService

logger = logging.getLogger(__name__)


def setup_database(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Application may not function correctly!")

def setup_filesystem(_: FastAPI):
    FilesystemService(settings).seed_default_templates()
    logger.info("Agent templates seeded.")

def setup_adapters(app: FastAPI):
    registry = AdapterRegistry()
    registry.register(ClaudeCodeAdapter())
    app.state.adapter_registry = registry

    logger.info(f"Adapters initialized: {registry.known_types()}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("Starting Zenve API")
    logger.info("=" * 60)

    setup_database(app)
    setup_filesystem(app)
    setup_adapters(app)

    yield

    engine.dispose()
    print("zenve API shutdown complete")
