import base64
import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta

import httpx
from jose import jwt

from zenve_config.settings import get_settings

GITHUB_API = "https://api.github.com"

# Cache: installation_id -> (token, expiry_unix_timestamp)
_token_cache: dict[int, tuple[str, float]] = {}
_TOKEN_TTL_SECONDS = 300  # 5 minutes (tokens last 1h, we refresh eagerly)


def mint_installation_token(installation_id: int) -> str:
    """Return a cached installation access token, refreshing if within TTL."""
    now = time.monotonic()
    cached = _token_cache.get(installation_id)
    if cached and cached[1] > now:
        return cached[0]

    settings = get_settings()
    private_key = settings.github_private_key
    if not settings.github_app_id or not private_key:
        raise RuntimeError("GitHub App credentials not configured")

    # GitHub App JWT: issued 60s in the past to tolerate clock drift
    iat = datetime.now(UTC) - timedelta(seconds=60)
    exp = datetime.now(UTC) + timedelta(minutes=9)
    app_jwt = jwt.encode(
        {"iss": str(settings.github_app_id), "iat": iat, "exp": exp},
        private_key,
        algorithm="RS256",
    )

    resp = httpx.post(
        f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
        },
    )
    resp.raise_for_status()
    token = resp.json()["token"]
    _token_cache[installation_id] = (token, now + _TOKEN_TTL_SECONDS)
    return token


def _auth_headers(installation_id: int) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {mint_installation_token(installation_id)}",
        "Accept": "application/vnd.github+json",
    }


def get_repo_info(installation_id: int, repo: str) -> dict:
    """Return the GitHub repo metadata dict."""
    resp = httpx.get(f"{GITHUB_API}/repos/{repo}", headers=_auth_headers(installation_id))
    resp.raise_for_status()
    return resp.json()


def get_repo_file(installation_id: int, repo: str, path: str, ref: str | None = None) -> bytes:
    """Fetch a file's raw bytes from a repo via the Contents API."""
    params = {"ref": ref} if ref else {}
    resp = httpx.get(
        f"{GITHUB_API}/repos/{repo}/contents/{path}",
        headers=_auth_headers(installation_id),
        params=params,
    )
    resp.raise_for_status()
    data = resp.json()
    return base64.b64decode(data["content"])


def list_repo_dir(installation_id: int, repo: str, path: str, ref: str | None = None) -> list[dict]:
    """List directory entries at path. Returns the raw GitHub API items."""
    params = {"ref": ref} if ref else {}
    resp = httpx.get(
        f"{GITHUB_API}/repos/{repo}/contents/{path}",
        headers=_auth_headers(installation_id),
        params=params,
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def list_tree_paths(
    installation_id: int, repo: str, prefix: str, ref: str | None = None
) -> list[str]:
    """Return all blob paths in the repo that start with prefix."""
    # Resolve the ref to a tree SHA
    ref_name = ref or "HEAD"
    resp = httpx.get(
        f"{GITHUB_API}/repos/{repo}/git/trees/{ref_name}",
        headers=_auth_headers(installation_id),
        params={"recursive": "1"},
    )
    resp.raise_for_status()
    tree = resp.json().get("tree", [])
    return [
        item["path"] for item in tree if item["type"] == "blob" and item["path"].startswith(prefix)
    ]


def commit_tree(
    installation_id: int,
    repo: str,
    branch: str,
    files: dict[str, bytes | None],
    message: str,
) -> str:
    """Commit files to the repo in a single commit. None value deletes the path.

    Returns the new commit SHA.
    """
    headers = _auth_headers(installation_id)

    # 1. Get current branch tip
    ref_resp = httpx.get(f"{GITHUB_API}/repos/{repo}/git/ref/heads/{branch}", headers=headers)
    ref_resp.raise_for_status()
    parent_sha = ref_resp.json()["object"]["sha"]

    # 2. Get base tree SHA from parent commit
    commit_resp = httpx.get(f"{GITHUB_API}/repos/{repo}/git/commits/{parent_sha}", headers=headers)
    commit_resp.raise_for_status()
    base_tree_sha = commit_resp.json()["tree"]["sha"]

    # 3. Create blobs for new/updated files
    tree_entries: list[dict] = []
    for path, content in files.items():
        if content is None:
            # Deletion: set sha to null
            tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
        else:
            blob_resp = httpx.post(
                f"{GITHUB_API}/repos/{repo}/git/blobs",
                headers=headers,
                json={"content": base64.b64encode(content).decode(), "encoding": "base64"},
            )
            blob_resp.raise_for_status()
            blob_sha = blob_resp.json()["sha"]
            tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob_sha})

    # 4. Create tree
    tree_resp = httpx.post(
        f"{GITHUB_API}/repos/{repo}/git/trees",
        headers=headers,
        json={"base_tree": base_tree_sha, "tree": tree_entries},
    )
    tree_resp.raise_for_status()
    new_tree_sha = tree_resp.json()["sha"]

    # 5. Create commit
    commit_create_resp = httpx.post(
        f"{GITHUB_API}/repos/{repo}/git/commits",
        headers=headers,
        json={"message": message, "tree": new_tree_sha, "parents": [parent_sha]},
    )
    commit_create_resp.raise_for_status()
    new_commit_sha = commit_create_resp.json()["sha"]

    # 6. Update branch ref
    httpx.patch(
        f"{GITHUB_API}/repos/{repo}/git/refs/heads/{branch}",
        headers=headers,
        json={"sha": new_commit_sha},
    ).raise_for_status()

    return new_commit_sha


def list_installation_repos(installation_id: int) -> list[dict]:
    """Return all repos accessible to the given GitHub App installation."""
    repos = []
    page = 1
    while True:
        r = httpx.get(
            f"{GITHUB_API}/installation/repositories",
            headers=_auth_headers(installation_id),
            params={"per_page": 100, "page": page},
        )
        r.raise_for_status()
        data = r.json()
        repos.extend(data["repositories"])
        if len(repos) >= data["total_count"]:
            break
        page += 1
    return repos


def verify_hmac_sha256(body: bytes, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 signature (GitHub or Zenve webhook format).

    Expects signature in 'sha256=<hex>' format.
    """
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    provided = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)
