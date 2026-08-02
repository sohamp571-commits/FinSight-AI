"""
database/crud.py

Purpose: Stateless, generic CRUD primitives that operate on an
explicit SQLAlchemy Session. These are the lowest-level building
blocks in the data layer -- they know nothing about business rules,
only about talking to a given model's table safely and consistently
(pagination, filtering, searching, sorting, bulk insert).

`base_service.py` wraps these functions with session management
(commit/rollback/close) and exception translation; concrete services
(user_service.py, portfolio_service.py, ...) should not call this
module directly -- they should go through BaseService instead.
"""

from typing import Any, TypeVar

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from database.models import Base

ModelType = TypeVar("ModelType", bound=Base)


def create(session: Session, instance: ModelType) -> ModelType:
    """Add a single ORM instance to the session and flush to obtain its PK."""
    session.add(instance)
    session.flush()
    session.refresh(instance)
    return instance


def bulk_create(session: Session, instances: list[ModelType]) -> list[ModelType]:
    """Add multiple ORM instances in a single flush (one round-trip)."""
    session.add_all(instances)
    session.flush()
    for instance in instances:
        session.refresh(instance)
    return instances


def get_by_id(session: Session, model: type[ModelType], record_id: Any, pk_column: str) -> ModelType | None:
    """Fetch a single record by primary key, or None if it doesn't exist."""
    stmt = select(model).where(getattr(model, pk_column) == record_id)
    return session.execute(stmt).scalar_one_or_none()


def get_one_by(session: Session, model: type[ModelType], **filters: Any) -> ModelType | None:
    """Fetch a single record matching exact-value column filters, or None."""
    stmt = select(model).filter_by(**filters)
    return session.execute(stmt).scalar_one_or_none()


def apply_filters(stmt, model: type[ModelType], filters: dict[str, Any] | None):
    """Apply a dict of {column_name: value} equality filters to a select statement."""
    if not filters:
        return stmt
    for column_name, value in filters.items():
        if value is None or not hasattr(model, column_name):
            continue
        stmt = stmt.where(getattr(model, column_name) == value)
    return stmt


def apply_search(stmt, model: type[ModelType], search_term: str | None, search_columns: list[str] | None):
    """Apply a case-insensitive substring search across one or more text columns (OR'd together)."""
    if not search_term or not search_columns:
        return stmt
    from sqlalchemy import or_

    conditions = [
        getattr(model, column).ilike(f"%{search_term}%")
        for column in search_columns
        if hasattr(model, column)
    ]
    if conditions:
        stmt = stmt.where(or_(*conditions))
    return stmt


def apply_sort(stmt, model: type[ModelType], sort_by: str | None, sort_direction: str = "asc"):
    """Apply ORDER BY to a select statement. Defaults to no-op if sort_by is invalid."""
    if not sort_by or not hasattr(model, sort_by):
        return stmt
    column = getattr(model, sort_by)
    return stmt.order_by(asc(column) if sort_direction.lower() == "asc" else desc(column))


def apply_pagination(stmt, page: int = 1, page_size: int = 25):
    """Apply LIMIT/OFFSET pagination to a select statement. page is 1-indexed."""
    page = max(page, 1)
    page_size = max(page_size, 1)
    return stmt.limit(page_size).offset((page - 1) * page_size)


def count_all(session: Session, model: type[ModelType], filters: dict[str, Any] | None = None) -> int:
    """Return the total row count for a model, optionally filtered."""
    stmt = select(func.count()).select_from(model)
    stmt = apply_filters(stmt, model, filters)
    return session.execute(stmt).scalar_one()


def list_records(
    session: Session,
    model: type[ModelType],
    filters: dict[str, Any] | None = None,
    search_term: str | None = None,
    search_columns: list[str] | None = None,
    sort_by: str | None = None,
    sort_direction: str = "asc",
    page: int = 1,
    page_size: int = 25,
) -> list[ModelType]:
    """
    Fetch a filtered, searched, sorted, and paginated list of records
    in a single call. This is the workhorse used by every service's
    `list_*` method.
    """
    stmt = select(model)
    stmt = apply_filters(stmt, model, filters)
    stmt = apply_search(stmt, model, search_term, search_columns)
    stmt = apply_sort(stmt, model, sort_by, sort_direction)
    stmt = apply_pagination(stmt, page, page_size)
    return list(session.execute(stmt).scalars().all())


def update_by_id(
    session: Session, model: type[ModelType], record_id: Any, pk_column: str, updates: dict[str, Any]
) -> ModelType | None:
    """Apply a dict of column updates to a record identified by primary key. Returns None if not found."""
    instance = get_by_id(session, model, record_id, pk_column)
    if instance is None:
        return None
    for key, value in updates.items():
        setattr(instance, key, value)
    session.flush()
    session.refresh(instance)
    return instance


def delete_by_id(session: Session, model: type[ModelType], record_id: Any, pk_column: str) -> bool:
    """Delete a record identified by primary key. Returns True if a row was deleted."""
    instance = get_by_id(session, model, record_id, pk_column)
    if instance is None:
        return False
    session.delete(instance)
    session.flush()
    return True
