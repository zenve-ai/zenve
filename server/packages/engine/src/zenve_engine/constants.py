from __future__ import annotations

# --- Paths & directory names ---
ZENVE_DIR = ".zenve"
SETTINGS_FILE = "settings.json"
AGENTS_SUBDIR = "agents"
CLAIMS_FILE = "claims.json"
SNAPSHOT_FILE = "snapshot.json"
TRANSCRIPTS_SUBDIR = "transcripts"
AGENTS_SKILLS_DIR = ".agents/skills"
CLAUDE_SKILLS_DIR = ".claude/skills"

# --- Remote repos ---
DEFAULT_REGISTRY_REPO = "zenve-ai/zenve-registry"
DEFAULT_AGENTS_PATH = "agents"
DEFAULT_SKILLS_PATH = "skills"

# --- GitHub API ---
GITHUB_API = "https://api.github.com"
GITHUB_DEFAULT_TIMEOUT = 30.0

# --- GitHub labels ---
CLAIMED_LABEL = "zenve:claimed"
FAILED_LABEL = "zenve:failed"
NEEDS_INPUT_LABEL = "zenve:needs-input"

# --- Timing ---
CLAIM_TTL_SECONDS = 3600
