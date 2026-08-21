from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import GOFUTURE, STARTING_COINS

logger = logging.getLogger(__name__)

# Persistent volume. Anything that must survive a redeploy — the SQLite file,
# downloaded photos and club badges — lives here and nowhere else.
DEFAULT_DATA_DIR = "/data"


def resolve_data_dir(preferred: str = DEFAULT_DATA_DIR) -> Path:
    """Use the persistent volume, falling back only if it cannot be written.

    On a host without /data (a developer laptop) the fallback keeps the app
    runnable instead of failing at import time, and says so in the log.
    """
    candidate = Path(preferred)
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return candidate
    except OSError:
        fallback = Path(__file__).resolve().parents[2] / "data"
        fallback.mkdir(parents=True, exist_ok=True)
        logger.warning("%s is not writable, using %s instead", preferred, fallback)
        return fallback


DATA_DIR = resolve_data_dir(os.getenv("DATA_DIR", DEFAULT_DATA_DIR))


def sqlite_url(path: Path) -> str:
    """Works for both /data/x.db and C:/data/x.db."""
    return f"sqlite+aiosqlite:///{path.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "GoF Cards"
    api_v1_prefix: str = "/api/v1"

    # the database lives on the persistent volume; docker-compose overrides
    # this with postgres+asyncpg
    data_dir: str = str(DATA_DIR)
    database_url: str = sqlite_url(DATA_DIR / "gof_cards.db")

    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # any origin on a private network (RFC1918) — lets a phone on the same
    # Wi-Fi reach the API directly without pinning the machine address
    cors_origin_regex: str = (
        r"^http://("
        r"localhost|127\.0\.0\.1"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|192\.168\.\d{1,3}\.\d{1,3}"
        r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?$"
    )

    gofuture_base_url: str = GOFUTURE["baseUrl"]
    gofuture_event_slug: str = GOFUTURE["eventSlug"]
    gofuture_tournament_slug: str = GOFUTURE["tournamentSlug"]
    sync_interval_seconds: int = 300
    sync_on_startup: bool = True

    starting_coins: int = STARTING_COINS


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
