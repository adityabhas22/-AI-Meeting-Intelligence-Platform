from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root, one level above backend/.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str
    openai_api_key: str
    openai_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    deepgram_api_key: str
    max_upload_mb: int = 200

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy async URL. Neon hands us a plain postgresql:// string;
        psycopg v3 is the driver that understands its sslmode/channel_binding."""
        url = self.database_url
        if url.startswith("postgresql+"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # fields come from env / .env
