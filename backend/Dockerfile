# Backend image for Railway (or any container host). A persistent container, so the
# background ingestion pipeline runs to completion (unlike request-scoped serverless).
FROM python:3.12-slim

# uv for fast, reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for better layer caching (no project install; package=false).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Apply migrations against DATABASE_URL, then serve. Railway provides $PORT.
CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
