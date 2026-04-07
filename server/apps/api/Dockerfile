# Build from workspace root: docker build -f apps/api/Dockerfile -t zenve-api .
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy workspace root config
COPY pyproject.toml uv.lock ./

# Copy all packages and the API app
COPY packages/ packages/
COPY apps/api/ apps/api/

# Install only the API app and its workspace dependencies
RUN uv sync --frozen --no-dev --no-cache --compile-bytecode --package zenve-api

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD [".venv/bin/api-start"]
