"""Integration test harness: an ephemeral pgvector Postgres (docker), migrated once
per session, with each test wrapped in a transaction that rolls back. Keeps tests
isolated and fast, and never touches the real Neon database."""

import os
import subprocess
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

# Docker Desktop on macOS exposes the daemon socket under the user's home, but the
# Python docker client defaults to /var/run/docker.sock. Point it at the real one
# before testcontainers imports the docker client.
_sock = Path.home() / ".docker" / "run" / "docker.sock"
if _sock.exists():
    os.environ.setdefault("DOCKER_HOST", f"unix://{_sock}")
# Ryuk (the reaper) can't bind-mount this socket on Docker Desktop; the context
# manager stops the container anyway, so disable it.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from testcontainers.postgres import PostgresContainer  # noqa: E402

from app.db import build_engine  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC = BACKEND_DIR / ".venv" / "bin" / "alembic"


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg17", username="test", password="test", dbname="test"
    ) as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        url = f"postgresql://test:test@{host}:{port}/test"
        subprocess.run(
            [str(ALEMBIC), "upgrade", "head"],
            cwd=BACKEND_DIR,
            env={**os.environ, "DATABASE_URL": url},
            check=True,
        )
        yield url


@pytest.fixture
async def db_session(pg_url: str) -> AsyncIterator[AsyncSession]:
    engine = build_engine(pg_url.replace("postgresql://", "postgresql+psycopg://", 1))
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
    await engine.dispose()
