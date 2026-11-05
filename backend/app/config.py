"""Configuración por variables de entorno (prefijo LOTOLAB_)."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOTOLAB_", env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{(DATA_DIR / 'lotolab.db').as_posix()}"
    raw_data_dir: Path = DATA_DIR / "raw"
    cache_dir: Path = DATA_DIR / "cache"
    backtest_summary_path: Path = DATA_DIR / "backtest_summary.json"
    expected_value_path: Path = DATA_DIR / "expected_value.json"
    picks_eval_path: Path = DATA_DIR / "picks_eval.json"
    ingest_token: str | None = None
    scraper_delay_seconds: float = 2.0
    scraper_user_agent: str = "LotoLab/0.1 (proyecto academico, no comercial)"
    # Orígenes permitidos para el frontend, separados por coma.
    cors_origins: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Render/Neon entregan postgres:// o postgresql://; SQLAlchemy necesita el driver."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
