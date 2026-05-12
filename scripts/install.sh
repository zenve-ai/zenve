#!/usr/bin/env sh
# Zenve CLI installer.
#
#   curl -fsSL https://raw.githubusercontent.com/zenve-ai/zenve/main/scripts/install.sh | sh
#
# Ensures Python 3.13+ and uv are available, then installs zenve-cli as a uv tool.

set -e

RED=$(printf '\033[31m')
GREEN=$(printf '\033[32m')
YELLOW=$(printf '\033[33m')
BOLD=$(printf '\033[1m')
RESET=$(printf '\033[0m')

info()  { printf "%s==>%s %s\n" "$GREEN" "$RESET" "$1"; }
warn()  { printf "%s!%s   %s\n" "$YELLOW" "$RESET" "$1"; }
error() { printf "%sx%s   %s\n" "$RED" "$RESET" "$1" >&2; }

# --- Python check ---
info "Checking for Python 3.13+..."
PY_OK=0
if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)' 2>/dev/null; then
        PY_OK=1
        info "Found $(python3 --version)"
    fi
fi

if [ "$PY_OK" -eq 0 ]; then
    warn "Python 3.13+ not found on PATH."
    warn "uv can install a managed Python for you — continuing."
fi

# --- uv check / install ---
if command -v uv >/dev/null 2>&1; then
    info "Found $(uv --version)"
else
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # uv's installer drops the binary in ~/.local/bin or ~/.cargo/bin and updates
    # the shell rc, but the current shell session won't know yet — source it.
    if [ -f "$HOME/.local/bin/env" ]; then
        # shellcheck disable=SC1091
        . "$HOME/.local/bin/env"
    fi
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if ! command -v uv >/dev/null 2>&1; then
        error "uv installation appears to have succeeded but 'uv' is not on PATH."
        error "Open a new shell and re-run this script, or add ~/.local/bin to PATH."
        exit 1
    fi
    info "Installed $(uv --version)"
fi

# --- Install zenve-cli ---
info "Installing zenve-cli..."
uv tool install --force zenve-cli

# --- Verify ---
if command -v zenve >/dev/null 2>&1; then
    printf "\n%sZenve installed successfully.%s\n" "$BOLD" "$RESET"
    zenve --version || true
    printf "\nNext steps:\n"
    printf "  zenve --help\n"
    printf "  zenve init           # scaffold .zenve/ in a repo\n"
else
    warn "zenve was installed but is not on PATH."
    warn "Run: uv tool update-shell    then open a new shell."
fi
