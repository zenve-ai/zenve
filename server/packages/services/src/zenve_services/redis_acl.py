from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class RedisACLService:
    """Manage per-org Redis ACL users with locked-down queue permissions.

    Creates a scoped ACL user on org creation and removes it on deletion.
    Uses short-lived connections — ACL operations are infrequent.
    Requires Redis 6+ with ACL support.
    """

    def __init__(self, redis_url: str, redis_password: str | None = None) -> None:
        self._url = redis_url
        self._password = redis_password

    async def create_org_user(self, slug: str, password: str) -> None:
        """Create a scoped Redis ACL user for an org's worker queue.

        Permissions granted:
          - Keys:     celery.worker.{slug}* and _kombu.binding.worker.{slug}*
          - Pub/sub:  all channels (&*)
          - Commands: LPUSH RPOP BRPOP LLEN (queue), SUBSCRIBE UNSUBSCRIBE PUBLISH (events)
        """
        import redis.asyncio as aioredis

        username = f"worker.{slug}"
        r = aioredis.from_url(self._url, password=self._password, decode_responses=True)
        try:
            await r.execute_command(
                "ACL",
                "SETUSER",
                username,
                "on",
                f">{password}",
                f"~celery.worker.{slug}*",
                f"~_kombu.binding.worker.{slug}*",
                "&*",
                "+LPUSH",
                "+RPOP",
                "+BRPOP",
                "+LLEN",
                "+SUBSCRIBE",
                "+UNSUBSCRIBE",
                "+PUBLISH",
            )
            logger.info("Created Redis ACL user: %s", username)
        finally:
            await r.aclose()

    async def delete_org_user(self, slug: str) -> None:
        """Remove the Redis ACL user for an org. Logs and continues on failure."""
        import redis.asyncio as aioredis

        username = f"worker.{slug}"
        r = aioredis.from_url(self._url, password=self._password, decode_responses=True)
        try:
            await r.execute_command("ACL", "DELUSER", username)
            logger.info("Deleted Redis ACL user: %s", username)
        except Exception:
            logger.exception(
                "Failed to delete Redis ACL user %s — flagged for manual cleanup", username
            )
        finally:
            await r.aclose()
