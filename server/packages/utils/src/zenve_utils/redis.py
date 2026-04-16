from urllib.parse import urlparse, urlunparse


def build_redis_worker_url(base_url: str, username: str, password: str) -> str:
    """Embed org worker credentials into the gateway's Redis URL."""
    p = urlparse(base_url)
    netloc = f"{username}:{password}@{p.hostname}"
    if p.port:
        netloc += f":{p.port}"
    return urlunparse(p._replace(netloc=netloc))
