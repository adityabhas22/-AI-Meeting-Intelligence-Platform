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
from app.extraction.schema import ExtractedActionItem, MeetingExtraction  # noqa: E402
from app.transcription.models import TranscriptionResult, TranscriptSegment  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC = BACKEND_DIR / ".venv" / "bin" / "alembic"


def fake_transcribe(audio: bytes, *, keyterms: list[str] | None = None) -> TranscriptionResult:
    return TranscriptionResult(
        segments=[
            TranscriptSegment(
                idx=0,
                speaker_label=0,
                start_sec=0.0,
                end_sec=5.0,
                text="We will ship Friday. Bob, can you deploy the auth fix?",
            ),
            TranscriptSegment(
                idx=1,
                speaker_label=1,
                start_sec=5.0,
                end_sec=10.0,
                text="Yes, I will deploy the auth fix by Friday.",
            ),
        ],
        duration_sec=10.0,
        language="en",
    )


def fake_extract(transcript: str) -> MeetingExtraction:
    return MeetingExtraction(
        title="Release planning",
        overview="The team agreed to ship on Friday.",
        attendees=["Alice", "Bob"],
        key_decisions=["Ship Friday"],
        discussion_points=["Auth fix"],
        open_questions=[],
        next_steps=["Review metrics next week"],
        action_items=[ExtractedActionItem(task="Deploy the auth fix", owner="Bob", due="Friday")],
        topics=["auth", "release"],
    )


def fake_embed(texts: list[str]) -> list[list[float]]:
    return [[0.1] * 1536 for _ in texts]


@pytest.fixture
def pipeline_fakes() -> dict:
    return {
        "transcribe_fn": fake_transcribe,
        "extract_fn": fake_extract,
        "embed_fn": fake_embed,
    }


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
