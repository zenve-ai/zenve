# Application Commands

start:
    uv run start

start-dev:
    API_RELOAD=true uv run start

# Development Commands

install:
    uv sync

add package:
    uv add {{package}}

add-dev package:
    uv add --dev {{package}}

update:
    uv lock --upgrade
    uv sync

# Docker

docker-build:
    docker build -t zenve:latest .

docker-up:
    docker compose up -d

docker-down:
    docker compose down

docker-logs:
    docker compose logs -f

# Code Quality

format:
    uv run ruff format .

lint path=".":
    uv run ruff check {{path}}

lint-fix path=".":
    uv run ruff check --fix {{path}}

typecheck path=".":
    uv run pyright {{path}}
