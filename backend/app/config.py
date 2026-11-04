"""Configuración por variables de entorno (prefijo LOTOLAB_)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOTOLAB_", env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{(DATA_DIR / 'lotolab.db').as_posix()}"
    raw_data_dir: Path = DATA_DIR / "raw"
    cache_dir: Path = DATA_DIR / "cache"
    ingest_token: str | None = None
    scraper_delay_seconds: float = 2.0
    scraper_user_agent: str = "LotoLab/0.1 (proyecto academico, no comercial)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
