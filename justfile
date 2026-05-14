default:
    @just --list

# ── Backend (server/) ──────────────────────────────────────────

api:
    cd server && just dev

runtime:
    cd server && just runtime

cli *args:
    cd server && just cli {{args}}

cli-link:
    cd server && just cli-link

migrate:
    cd server && just migrate

migrate-down:
    cd server && just migrate-down

migrate-gen msg="migration":
    cd server && just migrate-gen "{{msg}}"

# ── Frontend (ui/) ─────────────────────────────────────────────

ui:
    cd ui && pnpm dev

ui-build:
    cd ui && pnpm build

ui-lint:
    cd ui && pnpm lint

ui-typecheck:
    cd ui && pnpm typecheck

ui-install:
    cd ui && pnpm install

# ── Full stack ─────────────────────────────────────────────────

# Run runtime + api + ui together
dev:
    #!/usr/bin/env bash
    set -e
    trap 'kill 0' EXIT INT TERM
    (cd server && just runtime) &
    (cd server && just dev) &
    (cd ui && pnpm dev) &
    wait
