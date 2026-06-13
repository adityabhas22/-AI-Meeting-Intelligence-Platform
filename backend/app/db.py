from collections.abc import AsyncIterator

from pgvector.psycopg import register_vector_async
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def build_engine(url: str) -> AsyncEngine:
    # prepare_threshold=None disables client-side prepared statements, which the
    # Neon pooled endpoint (PgBouncer, transaction mode) does not support.
    engine = create_async_engine(url, pool_pre_ping=True, connect_args={"prepare_threshold": None})

    @event.listens_for(engine.sync_engine, "connect")
    def _register_vector(dbapi_conn, _record):  # noqa: ANN001
        # Make pgvector types round-trip on every pooled connection.
        dbapi_conn.run_async(register_vector_async)

    return engine


engine: AsyncEngine = build_engine(get_settings().async_database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
