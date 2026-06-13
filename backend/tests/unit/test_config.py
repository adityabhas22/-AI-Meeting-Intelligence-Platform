from app.config import Settings

_REQUIRED = {"openai_api_key": "x", "deepgram_api_key": "y"}


def test_plain_postgres_url_is_rewritten_to_psycopg():
    s = Settings(database_url="postgresql://u:p@h/db?sslmode=require", **_REQUIRED)
    assert s.async_database_url == "postgresql+psycopg://u:p@h/db?sslmode=require"


def test_psycopg_url_is_left_alone():
    s = Settings(database_url="postgresql+psycopg://u:p@h/db", **_REQUIRED)
    assert s.async_database_url == "postgresql+psycopg://u:p@h/db"


def test_defaults_applied():
    s = Settings(database_url="postgresql://u:p@h/db", **_REQUIRED)
    assert s.openai_model == "gpt-5-mini"
    assert s.openai_embedding_model == "text-embedding-3-small"
