"""
config.py

Loads and validates all application configuration from environment
variables (via a local .env file during development). Exposes a single
`config` singleton that every other module imports, so configuration is
read once and never duplicated.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from custom_exceptions import ConfigurationError
from urllib.parse import quote_plus

# ----------------------------------------------------------
# Locate project root and load .env before anything else runs
# ----------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
ENV_PATH: Path = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # Fall back to any .env discoverable on the standard search path.
    load_dotenv()


def _get_env(key: str, default: str | None = None, required: bool = False) -> str | None:
    """Fetch an environment variable, optionally enforcing that it exists."""
    value = os.getenv(key, default)
    if required and (value is None or value.strip() == ""):
        raise ConfigurationError(f"Required environment variable '{key}' is not set.")
    return value


def _get_bool_env(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_int_env(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable '{key}' must be an integer.") from exc


class Config:
    """
    Immutable-by-convention configuration object for FinSight AI.

    All values are resolved once at import time from environment
    variables. Instantiate via the module-level `config` singleton
    rather than creating new Config() instances elsewhere.
    """

    # --------------- Paths ---------------
    BASE_DIR: Path = BASE_DIR

    # --------------- Application ---------------
    APP_NAME: str = _get_env("APP_NAME", default="FinSight AI")
    APP_ENV: str = _get_env("APP_ENV", default="development")
    APP_DEBUG: bool = _get_bool_env("APP_DEBUG", default=True)
    SECRET_KEY: str = _get_env("SECRET_KEY", default="dev-secret-key-change-me")

    # --------------- Database ---------------
    DB_HOST: str = _get_env("DB_HOST", default="localhost")
    DB_PORT: int = _get_int_env("DB_PORT", default=3306)
    DB_NAME: str = _get_env("DB_NAME", default="finsight_ai")
    DB_USER: str = _get_env("DB_USER", default="root")
    DB_PASSWORD: str = _get_env("DB_PASSWORD", default="")
    DB_POOL_SIZE: int = _get_int_env("DB_POOL_SIZE", default=10)
    DB_POOL_RECYCLE: int = _get_int_env("DB_POOL_RECYCLE", default=3600)

    # --------------- External APIs ---------------
    NEWS_API_KEY: str | None = _get_env("NEWS_API_KEY", default=None)

    # --------------- Logging ---------------
    LOG_LEVEL: str = _get_env("LOG_LEVEL", default="INFO")
    LOG_DIR: str = _get_env("LOG_DIR", default="logs")

    # --------------- Security ---------------
    BCRYPT_ROUNDS: int = _get_int_env("BCRYPT_ROUNDS", default=12)
    SESSION_TIMEOUT_MINUTES: int = _get_int_env("SESSION_TIMEOUT_MINUTES", default=60)

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Build the MySQL connection string used by SQLAlchemy's create_engine()."""
        return (
            f"mysql+pymysql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    def validate(self) -> None:
        """
        Run sanity checks on critical configuration values.
        Call this once at application startup (see app.py).
        """
        if self.APP_ENV not in ("development", "staging", "production"):
            raise ConfigurationError(
                f"APP_ENV must be one of development/staging/production, got '{self.APP_ENV}'."
            )
        if self.DB_PORT <= 0 or self.DB_PORT > 65535:
            raise ConfigurationError(f"DB_PORT '{self.DB_PORT}' is not a valid port number.")
        if self.APP_ENV == "production" and self.SECRET_KEY == "dev-secret-key-change-me":
            raise ConfigurationError("SECRET_KEY must be changed before running in production.")


# Module-level singleton imported throughout the project: `from config import config`
config = Config()
