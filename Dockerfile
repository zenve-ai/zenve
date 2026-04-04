# Build: docker build -t zenve .
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev --no-cache

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD [".venv/bin/start"]
