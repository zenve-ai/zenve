import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_adapters.open_code import OpenCodeAdapter
from zenve_adapters.registry import AdapterRegistry
from zenve_db.database import Base, engine
from zenve_services.ws_manager import WebSocketManager

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


def setup_adapters(app: FastAPI):
    registry = AdapterRegistry()
    registry.register(ClaudeCodeAdapter())
    registry.register(OpenCodeAdapter())
    app.state.adapter_registry = registry

    logger.info(f"Adapters initialized: {registry.known_types()}")


def setup_ws(app: FastAPI) -> WebSocketManager:
    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager
    logger.info("WebSocket ready at ws://0.0.0.0:8000/api/v1/orgs/{org_id}/ws")
    return ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("Starting Zenve API")
    logger.info("=" * 60)

    setup_database(app)
    setup_adapters(app)
    setup_ws(app)

    yield

    engine.dispose()
    print("zenve API shutdown complete")
