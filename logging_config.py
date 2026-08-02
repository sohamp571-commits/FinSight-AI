"""
logging_config.py

Configures a single, project-wide loguru logger. Every module should
import `logger` from this file (`from logging_config import logger`)
instead of creating its own logging handlers, so log output stays
consistent and centralized under /logs.
"""

import sys
from pathlib import Path

from loguru import logger

from config import config

# ----------------------------------------------------------
# Ensure the log directory exists
# ----------------------------------------------------------
LOG_DIR: Path = config.BASE_DIR / config.LOG_DIR
LOG_DIR.mkdir(parents=True, exist_ok=True)

APP_LOG_FILE: Path = LOG_DIR / "app.log"
ERROR_LOG_FILE: Path = LOG_DIR / "error.log"

# ----------------------------------------------------------
# Reset default handlers so we control formatting/sinks explicitly
# ----------------------------------------------------------
logger.remove()

# Console sink -- human-readable, colorized
logger.add(
    sys.stdout,
    level=config.LOG_LEVEL,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
    backtrace=False,
    diagnose=config.APP_DEBUG,
)

# Rotating file sink -- all levels
logger.add(
    APP_LOG_FILE,
    level=config.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    backtrace=False,
    diagnose=False,
)

# Dedicated error/critical file sink for fast incident triage
logger.add(
    ERROR_LOG_FILE,
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}",
    rotation="10 MB",
    retention="60 days",
    compression="zip",
    encoding="utf-8",
    backtrace=True,
    diagnose=False,
)

logger.info(f"Logging initialized for {config.APP_NAME} (env={config.APP_ENV})")

__all__ = ["logger"]
