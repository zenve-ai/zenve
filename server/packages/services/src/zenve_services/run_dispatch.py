from __future__ import annotations

import json

import redis as sync_redis


class RunDispatchService:
    def __init__(self, redis_url: str, redis_password: str | None = None) -> None:
        self.client = sync_redis.Redis.from_url(redis_url, password=redis_password)

    def publish_run(self, org_slug: str, run_id: str) -> None:
        payload = json.dumps({"run_id": run_id})
        self.client.publish(f"runs:dispatch:{org_slug}", payload)

    def close(self) -> None:
        self.client.close()
