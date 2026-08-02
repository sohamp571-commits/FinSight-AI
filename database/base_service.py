"""
database/base_service.py

Purpose: Generic service base class providing full CRUD (create, read,
update, delete, bulk insert, pagination, filtering, searching,
sorting) with proper session/transaction management and exception
translation. Every domain service (UserService, PortfolioService, ...)
subclasses BaseService[Model] and adds only its domain-specific
methods, instead of re-implementing session handling each time.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from custom_exceptions import DatabaseQueryError, DuplicateRecordError, RecordNotFoundError
from database import crud
from database.connection import db_connection
from database.models import Base
from logging_config import logger

ModelType = TypeVar("ModelType", bound=Base)


class BaseService(Generic[ModelType]):
    """
    Generic CRUD service bound to a single SQLAlchemy model.

    Subclasses set `model` and `pk_column` and inherit full CRUD
    behavior. Every method opens its own session via
    `db_connection.get_session()`, which commits on success and
    rolls back automatically on any exception (see connection.py).
    """

    model: type[ModelType]
    pk_column: str = "id"

    def __init__(self) -> None:
        if not hasattr(self, "model"):
            raise NotImplementedError("Subclasses of BaseService must define `model`.")
        self._db = db_connection

    # ------------------------------------------------------
    # Create
    # ------------------------------------------------------
    def create(self, instance: ModelType) -> ModelType:
        """Insert a single new record."""
        try:
            with self._db.get_session() as session:
                created = crud.create(session, instance)
                session.expunge(created)
                logger.info(f"{self.model.__name__} created (pk={getattr(created, self.pk_column, None)}).")
                return created
        except IntegrityError as exc:
            logger.warning(f"Duplicate {self.model.__name__} rejected: {exc}")
            raise DuplicateRecordError(f"This {self.model.__name__} already exists.") from exc
        except SQLAlchemyError as exc:
            logger.error(f"Failed to create {self.model.__name__}: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def bulk_create(self, instances: list[ModelType]) -> list[ModelType]:
        """Insert multiple new records in a single transaction."""
        if not instances:
            return []
        try:
            with self._db.get_session() as session:
                created = crud.bulk_create(session, instances)
                for item in created:
                    session.expunge(item)
                logger.info(f"Bulk-created {len(created)} {self.model.__name__} record(s).")
                return created
        except IntegrityError as exc:
            logger.warning(f"Bulk insert rejected due to a duplicate: {exc}")
            raise DuplicateRecordError(f"One or more {self.model.__name__} records already exist.") from exc
        except SQLAlchemyError as exc:
            logger.error(f"Failed to bulk-create {self.model.__name__}: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Read
    # ------------------------------------------------------
    def get_by_id(self, record_id: Any) -> ModelType:
        """Fetch a single record by primary key, raising if not found."""
        try:
            with self._db.get_session() as session:
                instance = crud.get_by_id(session, self.model, record_id, self.pk_column)
                if instance is None:
                    raise RecordNotFoundError(
                        f"{self.model.__name__} with {self.pk_column}={record_id} not found."
                    )
                session.expunge(instance)
                return instance
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch {self.model.__name__}: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def find_one_by(self, **filters: Any) -> ModelType | None:
        """Fetch a single record matching exact-value filters, or None."""
        try:
            with self._db.get_session() as session:
                instance = crud.get_one_by(session, self.model, **filters)
                if instance is not None:
                    session.expunge(instance)
                return instance
        except SQLAlchemyError as exc:
            logger.error(f"Failed to find {self.model.__name__} by filter: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def list(
        self,
        filters: dict[str, Any] | None = None,
        search_term: str | None = None,
        search_columns: list[str] | None = None,
        sort_by: str | None = None,
        sort_direction: str = "asc",
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        """
        Fetch a filtered, searched, sorted, paginated page of records.

        Returns:
            {"items": [...], "total": int, "page": int, "page_size": int, "total_pages": int}
        """
        try:
            with self._db.get_session() as session:
                items = crud.list_records(
                    session,
                    self.model,
                    filters=filters,
                    search_term=search_term,
                    search_columns=search_columns,
                    sort_by=sort_by,
                    sort_direction=sort_direction,
                    page=page,
                    page_size=page_size,
                )
                total = crud.count_all(session, self.model, filters=filters)
                for item in items:
                    session.expunge(item)

                total_pages = (total + page_size - 1) // page_size if page_size else 1
                return {
                    "items": items,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": max(total_pages, 1),
                }
        except SQLAlchemyError as exc:
            logger.error(f"Failed to list {self.model.__name__}: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Return the total number of records matching optional filters."""
        try:
            with self._db.get_session() as session:
                return crud.count_all(session, self.model, filters=filters)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to count {self.model.__name__}: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------
    def update(self, record_id: Any, updates: dict[str, Any]) -> ModelType:
        """Apply a dict of column updates to a record identified by primary key."""
        try:
            with self._db.get_session() as session:
                instance = crud.update_by_id(session, self.model, record_id, self.pk_column, updates)
                if instance is None:
                    raise RecordNotFoundError(
                        f"{self.model.__name__} with {self.pk_column}={record_id} not found."
                    )
                session.expunge(instance)
                logger.info(f"{self.model.__name__} updated (pk={record_id}).")
                return instance
        except IntegrityError as exc:
            logger.warning(f"Update to {self.model.__name__} violated a constraint: {exc}")
            raise DuplicateRecordError("This update conflicts with an existing record.") from exc
        except SQLAlchemyError as exc:
            logger.error(f"Failed to update {self.model.__name__}: {exc}")
            raise DatabaseQueryError(str(exc)) from exc

    # ------------------------------------------------------
    # Delete
    # ------------------------------------------------------
    def delete(self, record_id: Any) -> None:
        """Hard-delete a record identified by primary key."""
        try:
            with self._db.get_session() as session:
                deleted = crud.delete_by_id(session, self.model, record_id, self.pk_column)
                if not deleted:
                    raise RecordNotFoundError(
                        f"{self.model.__name__} with {self.pk_column}={record_id} not found."
                    )
                logger.info(f"{self.model.__name__} deleted (pk={record_id}).")
        except SQLAlchemyError as exc:
            logger.error(f"Failed to delete {self.model.__name__}: {exc}")
            raise DatabaseQueryError(str(exc)) from exc
