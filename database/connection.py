"""
database/connection.py

Owns the SQLAlchemy Engine and session factory for the whole project.
Every other module should obtain a session via `get_session()` (a
context manager) rather than creating its own engine.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from config import config
from custom_exceptions import DatabaseConnectionError
from logging_config import logger


class DatabaseConnection:
    """
    Wraps a single SQLAlchemy Engine + sessionmaker for the application.

    Implemented as a lazily-initialized singleton so that only one
    connection pool is ever created per process, no matter how many
    modules import this class.
    """

    _instance: "DatabaseConnection | None" = None
    _engine: Engine | None = None
    _session_factory: sessionmaker | None = None

    def __new__(cls) -> "DatabaseConnection":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Create the engine and session factory. Called once per process."""
        try:
            self._engine = create_engine(
                config.SQLALCHEMY_DATABASE_URI,
                pool_size=config.DB_POOL_SIZE,
                pool_recycle=config.DB_POOL_RECYCLE,
                pool_pre_ping=True,
                echo=False,
                future=True,
            )
            self._session_factory = sessionmaker(
                bind=self._engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
            logger.info(
                f"Database engine initialized -> "
                f"{config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
            )
        except SQLAlchemyError as exc:
            logger.error(f"Failed to initialize database engine: {exc}")
            raise DatabaseConnectionError(str(exc)) from exc

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._initialize()
        return self._engine

    def test_connection(self) -> bool:
        """Ping the database to confirm connectivity. Returns True/False."""
        try:
            with self.engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            logger.info("Database connection test succeeded.")
            return True
        except SQLAlchemyError as exc:
            logger.error(f"Database connection test failed: {exc}")
            return False

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager yielding a SQLAlchemy Session with automatic
        commit/rollback/close handling.

        Usage:
            with db_connection.get_session() as session:
                session.add(some_object)
        """
        if self._session_factory is None:
            self._initialize()

        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            logger.error(f"Session rolled back due to error: {exc}")
            raise DatabaseConnectionError(str(exc)) from exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@event.listens_for(Engine, "connect")
def _set_mysql_session_settings(dbapi_connection, connection_record) -> None:
    """Ensure every new MySQL connection uses UTF-8 and strict SQL mode."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET NAMES utf8mb4")
        cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE'")
    finally:
        cursor.close()


# Module-level singleton used throughout the project.
db_connection = DatabaseConnection()
