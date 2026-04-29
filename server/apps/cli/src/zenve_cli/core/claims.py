from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from zenve_cli.core.config import zenve_dir
from zenve_cli.models.claims import Claim, ClaimsFile

CLAIMS_FILE = "claims.json"
CLAIM_TTL_SECONDS = 3600

_lock = threading.Lock()


def claims_file_path(repo_root: Path) -> Path:
    return zenve_dir(repo_root) / CLAIMS_FILE


def load_claims(repo_root: Path) -> ClaimsFile:
    path = claims_file_path(repo_root)
    if not path.exists():
        return ClaimsFile()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return ClaimsFile.model_validate(raw)
    except Exception:
        return ClaimsFile()


def save_claims(repo_root: Path, cf: ClaimsFile) -> None:
    path = claims_file_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(cf.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)


def add_claim(repo_root: Path, claim: Claim) -> None:
    with _lock:
        cf = load_claims(repo_root)
        cf.claims = [c for c in cf.claims if c.number != claim.number]
        cf.claims.append(claim)
        save_claims(repo_root, cf)


def remove_claim(repo_root: Path, number: int) -> None:
    with _lock:
        cf = load_claims(repo_root)
        cf.claims = [c for c in cf.claims if c.number != number]
        save_claims(repo_root, cf)


def expired_claims(repo_root: Path) -> list[Claim]:
    cf = load_claims(repo_root)
    cutoff = datetime.now(UTC) - timedelta(seconds=CLAIM_TTL_SECONDS)
    result: list[Claim] = []
    for c in cf.claims:
        try:
            claimed_dt = datetime.fromisoformat(c.claimed_at.replace("Z", "+00:00"))
        except ValueError:
            result.append(c)
            continue
        if claimed_dt < cutoff:
            result.append(c)
    return result
