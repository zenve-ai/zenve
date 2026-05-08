# Build from workspace root: docker build -f apps/runtime/Dockerfile -t zenve-runtime .
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy workspace root config
COPY pyproject.toml uv.lock ./

# Copy all packages and the runtime app
COPY packages/ packages/
COPY apps/runtime/ apps/runtime/

# Install only the runtime app and its workspace dependencies
RUN uv sync --frozen --no-dev --no-cache --compile-bytecode --package zenve-runtime

ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD [".venv/bin/runtime-start"]
