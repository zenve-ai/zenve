import shutil

KNOWN_RUNTIMES: dict[str, str] = {
    "claude": "claude_code",
    "codex": "codex",
    "opencode": "opencode",
}


def detect_runtimes() -> list[str]:
    """Return list of binary names (e.g. 'claude') that are on PATH."""
    return [bin_name for bin_name in KNOWN_RUNTIMES if shutil.which(bin_name)]
