"""
database/database.py

A thin, generic data-access layer built on top of database/connection.py.
Feature modules (authentication, portfolio, etc. in later phases) should
use DatabaseManager instead of talking to SQLAlchemy sessions directly,
so that error handling and logging stay consistent everywhere.
"""

from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from custom_exceptions import DatabaseQueryError, DuplicateRecordError, RecordNotFoundError
from database.connection import db_connection
from database.models import Base
from logging_config import logger

ModelType = TypeVar("ModelType", bound=Base)


class DatabaseManager:
    """Generic CRUD helper that works against any SQLAlchemy ORM model."""

    def __init__(self) -> None:
        self._db = db_connection

    # ------------------------------------------------------
    # Create
    # ------------------------------------------------------
    def add(self, instance: ModelType) -> ModelType:
        """Insert a single ORM instance and return it (with its generated PK)."""
        try:
            with self._db.get_session() as session:
                session.add(instance)
                session.flush()
                session.refresh(instance)
                session.expunge(instance)
                return instance
        except IntegrityError as exc:
            logger.warning(f"Duplicate record rejected: {exc}")
            raise DuplicateRecordError("A record with these details already exists.") from exc
        except SQLAlchemyError as exc:
            logger.error(f"Failed to add record: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Read
    # ------------------------------------------------------
    def get_by_id(self, model: type[ModelType], record_id: Any, pk_column: str) -> ModelType:
        """Fetch a single record by primary key, raising if not found."""
        try:
            with self._db.get_session() as session:
                stmt = select(model).where(getattr(model, pk_column) == record_id)
                result = session.execute(stmt).scalar_one_or_none()
                if result is None:
                    raise RecordNotFoundError(f"{model.__name__} with {pk_column}={record_id} not found.")
                session.expunge(result)
                return result
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch record: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def get_all(self, model: type[ModelType], limit: int = 100, offset: int = 0) -> list[ModelType]:
        """Fetch a paginated list of records for a given model."""
        try:
            with self._db.get_session() as session:
                stmt = select(model).limit(limit).offset(offset)
                results = list(session.execute(stmt).scalars().all())
                for row in results:
                    session.expunge(row)
                return results
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch records: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def find_one_by(self, model: type[ModelType], **filters: Any) -> ModelType | None:
        """Fetch a single record matching arbitrary column filters, or None."""
        try:
            with self._db.get_session() as session:
                stmt = select(model).filter_by(**filters)
                result = session.execute(stmt).scalar_one_or_none()
                if result is not None:
                    session.expunge(result)
                return result
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch record by filter: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------
    def update(self, model: type[ModelType], record_id: Any, pk_column: str, updates: dict[str, Any]) -> ModelType:
        """Apply a dict of column updates to a record identified by primary key."""
        try:
            with self._db.get_session() as session:
                stmt = select(model).where(getattr(model, pk_column) == record_id)
                instance = session.execute(stmt).scalar_one_or_none()
                if instance is None:
                    raise RecordNotFoundError(f"{model.__name__} with {pk_column}={record_id} not found.")
                for key, value in updates.items():
                    setattr(instance, key, value)
                session.flush()
                session.refresh(instance)
                session.expunge(instance)
                return instance
        except IntegrityError as exc:
            logger.warning(f"Update violated a constraint: {exc}")
            raise DuplicateRecordError("Update conflicts with an existing record.") from exc
        except SQLAlchemyError as exc:
            logger.error(f"Failed to update record: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Delete
    # ------------------------------------------------------
    def delete(self, model: type[ModelType], record_id: Any, pk_column: str) -> None:
        """Delete a record identified by primary key."""
        try:
            with self._db.get_session() as session:
                stmt = select(model).where(getattr(model, pk_column) == record_id)
                instance = session.execute(stmt).scalar_one_or_none()
                if instance is None:
                    raise RecordNotFoundError(f"{model.__name__} with {pk_column}={record_id} not found.")
                session.delete(instance)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to delete record: {exc}")
            raise DatabaseQueryError(str(exc)) from exc


# Module-level singleton used throughout the project.
db_manager = DatabaseManager()
