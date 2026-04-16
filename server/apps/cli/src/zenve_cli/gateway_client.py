import logging

import httpx

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Gateway error {status_code}: {body}")


class GatewayClient:
    def __init__(self, gateway_url: str, api_key: str) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_error:
            logger.error(
                "Gateway %s %s → %s", response.request.method, response.url, response.status_code
            )
            raise GatewayError(response.status_code, response.text)

    def verify_credentials(self) -> dict:
        resp = self.client.get(f"{self.gateway_url}/worker/org")
        self._raise_for_status(resp)
        return resp.json()

    def register_worker(self, org_slug: str, queue: str, runtimes: list[str]) -> dict:
        resp = self.client.post(
            f"{self.gateway_url}/worker/register",
            json={"org_slug": org_slug, "queue": queue, "runtimes": runtimes},
        )
        self._raise_for_status(resp)
        return resp.json()

    def get_run_context(self, run_id: str) -> dict:
        resp = self.client.get(f"{self.gateway_url}/worker/runs/{run_id}/context")
        self._raise_for_status(resp)
        return resp.json()

    def complete_run(self, run_id: str, payload: dict) -> dict:
        resp = self.client.post(
            f"{self.gateway_url}/worker/runs/{run_id}/complete",
            json=payload,
        )
        self._raise_for_status(resp)
        return resp.json()

    def close(self) -> None:
        self.client.close()
