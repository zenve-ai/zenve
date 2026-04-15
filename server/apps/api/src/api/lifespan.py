import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_adapters.open_code import OpenCodeAdapter
from zenve_adapters.registry import AdapterRegistry
from zenve_config.settings import get_settings
from zenve_db.database import Base, Session, engine
from zenve_db.models import Run
from zenve_models.run_event import RunEventResponse
from zenve_scaffolding import ScaffoldingService
from zenve_services.run_event import RunEventService
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


def setup_filesystem(_: FastAPI):
    ScaffoldingService(get_settings()).seed_default_templates()
    logger.info("Agent templates seeded.")


def setup_adapters(app: FastAPI):
    registry = AdapterRegistry()
    registry.register(ClaudeCodeAdapter())
    registry.register(OpenCodeAdapter())
    app.state.adapter_registry = registry

    logger.info(f"Adapters initialized: {registry.known_types()}")


async def run_redis_subscriber(ws_manager: WebSocketManager, redis_url: str, redis_password: str | None = None) -> None:
    """Background task: subscribe to run:*:events pub/sub and push to WebSocket clients."""
    try:
        import redis.asyncio as aioredis
    except ImportError:
        logger.warning("redis.asyncio not available — Redis subscriber disabled")
        return

    r = aioredis.from_url(redis_url, password=redis_password)
    pubsub = r.pubsub()
    await pubsub.psubscribe("run:*:events")
    logger.info("Redis subscriber listening on run:*:events")

    try:
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            try:
                data = json.loads(message["data"])
                channel: str = message["channel"]
                # channel format: run:{run_id}:events
                parts = channel.split(":")
                if len(parts) < 2:
                    continue
                run_id = parts[1]

                event_type = data.get("event_type", "")
                content = data.get("content")
                meta = data.get("meta")

                db = Session()
                try:
                    run: Run | None = db.get(Run, run_id)
                    if not run:
                        continue
                    org_id = run.org_id
                    event = RunEventService(db).create(
                        run_id=run_id, event_type=event_type, content=content, meta=meta
                    )
                    payload = {
                        "type": "run.event",
                        "data": RunEventResponse.model_validate(event).model_dump(mode="json"),
                    }
                    await ws_manager.broadcast(org_id, payload)
                except Exception:
                    logger.exception("Redis subscriber: failed to handle event for run %s", run_id)
                finally:
                    db.close()
            except Exception:
                logger.exception("Redis subscriber: error processing message")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe()
        await r.aclose()
        logger.info("Redis subscriber stopped")


def setup_ws(app: FastAPI) -> WebSocketManager:
    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager
    logger.info("WebSocket ready at ws://0.0.0.0:8000/api/v1/orgs/{org_id}/ws")
    return ws_manager


async def setup_redis(ws_manager: WebSocketManager) -> asyncio.Task | None:
    settings = get_settings()
    redis_url = settings.redis_url
    if redis_url:
        task = asyncio.create_task(run_redis_subscriber(ws_manager, redis_url, settings.redis_password))
        logger.info("Redis event subscriber started")
        return task
    logger.info("No REDIS_URL configured — Redis event subscriber disabled")
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("Starting Zenve API")
    logger.info("=" * 60)

    setup_database(app)
    setup_filesystem(app)
    setup_adapters(app)
    ws_manager = setup_ws(app)
    subscriber_task = await setup_redis(ws_manager)

    yield

    if subscriber_task:
        subscriber_task.cancel()
        try:
            await subscriber_task
        except asyncio.CancelledError:
            pass

    engine.dispose()
    print("zenve API shutdown complete")
