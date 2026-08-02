"""
database/init_db.py

Purpose: One-shot initialization script that gets a fresh MySQL
instance ready to run FinSight AI. Run this once per environment
(local dev, staging, ...) after configuring `.env`.

Steps performed:
    1. Create the target database if it doesn't already exist.
    2. Verify connectivity through the normal application engine.
    3. Create every table defined in database/models.py.
    4. Seed the default roles (admin, analyst, user).
    5. Create a default admin account (idempotent -- skipped if one
       already exists).
    6. Print a human-readable summary.

Run with:  python database/init_db.py
(Run from the project root so relative imports resolve correctly --
 PyCharm's default "Run" configuration does this automatically when
 init_db.py is set as the script and the project root is the working
 directory.)
"""

import sys
from pathlib import Path

# Allow running this file directly (e.g. `python database/init_db.py`)
# by ensuring the project root is on sys.path, matching how PyCharm
# resolves imports when the project root is marked as Sources Root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pymysql  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from config import config  # noqa: E402
from constants import UserRole  # noqa: E402
from custom_exceptions import ConfigurationError, DatabaseConnectionError, FinSightBaseException  # noqa: E402
from logging_config import logger  # noqa: E402


def create_database_if_missing() -> None:
    """
    Connect to the MySQL server WITHOUT selecting a database (since
    the target database may not exist yet) and issue CREATE DATABASE
    IF NOT EXISTS. Uses PyMySQL directly rather than SQLAlchemy's
    engine, because the engine's connection string always targets a
    specific database name.
    """
    logger.info(f"Ensuring database '{config.DB_NAME}' exists...")
    try:
        connection = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            charset="utf8mb4",
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            connection.commit()
            logger.info(f"Database '{config.DB_NAME}' is ready.")
        finally:
            connection.close()
    except pymysql.MySQLError as exc:
        logger.error(f"Failed to create database '{config.DB_NAME}': {exc}")
        raise DatabaseConnectionError(
            f"Could not create or reach database '{config.DB_NAME}'. "
            f"Check DB_HOST/DB_PORT/DB_USER/DB_PASSWORD in your .env file."
        ) from exc


def verify_connection() -> None:
    """Verify the application's SQLAlchemy engine can reach the newly-created database."""
    from database.connection import db_connection

    logger.info("Verifying database connectivity through the application engine...")
    if not db_connection.test_connection():
        raise DatabaseConnectionError("Database connection verification failed after creation.")
    logger.info("Database connectivity verified.")


def create_tables() -> None:
    """
    Create every table defined by the SQLAlchemy models in
    database/models.py. This is the portable, PyCharm-friendly path
    for local development; database/schema.sql remains available as
    the fully-specified DDL reference (exact ENUM types, etc.) for
    manual execution in MySQL Workbench or a DBA review.
    """
    from database.connection import db_connection
    from database.models import Base

    logger.info("Creating tables from SQLAlchemy models (idempotent)...")
    try:
        Base.metadata.create_all(bind=db_connection.engine)
        logger.info("All tables created (or already existed).")
    except SQLAlchemyError as exc:
        logger.error(f"Failed to create tables: {exc}")
        raise DatabaseConnectionError(str(exc)) from exc


def seed_default_roles() -> None:
    """Insert the three default roles if they don't already exist."""
    from database.database import db_manager
    from database.models import Role

    logger.info("Seeding default roles...")
    default_roles = [
        (UserRole.ADMIN.value, "Full administrative access to the platform"),
        (UserRole.ANALYST.value, "Elevated access to analytics and reporting tools"),
        (UserRole.USER.value, "Standard end-user access"),
    ]

    for role_name, description in default_roles:
        existing = db_manager.find_one_by(Role, role_name=role_name)
        if existing is None:
            db_manager.add(Role(role_name=role_name, description=description))
            logger.info(f"Role created: {role_name}")
        else:
            logger.info(f"Role already exists, skipping: {role_name}")


def create_default_admin() -> None:
    """
    Create a default admin account if one doesn't already exist, using
    credentials from the .env file. Skipped entirely (idempotent) on
    subsequent runs once an admin with that email is present.
    """
    from authentication.password_utils import create_password_hash
    from database.database import db_manager
    from database.models import Role, User

    admin_email = "admin@finsight.ai"
    admin_username = "admin"
    admin_password = "Admin@12345"  # noqa: S105 - default dev credential, must be changed after first login

    logger.info("Checking for an existing admin account...")
    existing_admin = db_manager.find_one_by(User, email=admin_email)
    if existing_admin is not None:
        logger.info("Admin account already exists, skipping creation.")
        return

    admin_role = db_manager.find_one_by(Role, role_name=UserRole.ADMIN.value)
    if admin_role is None:
        raise ConfigurationError("Admin role must be seeded before creating the admin account.")

    admin_user = User(
        full_name="FinSight Administrator",
        email=admin_email,
        username=admin_username,
        password_hash=create_password_hash(admin_password),
        role_id=admin_role.role_id,
        is_active=True,
    )
    db_manager.add(admin_user)
    logger.warning(
        f"Default admin account created -> username: '{admin_username}', "
        f"password: '{admin_password}'. CHANGE THIS PASSWORD IMMEDIATELY after first login."
    )


def run_initialization() -> None:
    """Execute every initialization step in order, with a summary at the end."""
    logger.info("=" * 60)
    logger.info(f"FinSight AI - Database Initialization (env={config.APP_ENV})")
    logger.info("=" * 60)

    try:
        config.validate()
        create_database_if_missing()
        verify_connection()
        create_tables()
        seed_default_roles()
        create_default_admin()

        logger.info("=" * 60)
        logger.info("Database initialization completed successfully.")
        logger.info("=" * 60)
        print("\n✅ FinSight AI database initialized successfully.")
        print("   Run the app with:  streamlit run app.py\n")

    except FinSightBaseException as exc:
        logger.error(f"Initialization failed: {exc.message}")
        print(f"\n❌ Database initialization failed: {exc.message}\n")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected error during initialization: {exc}")
        print(f"\n❌ Unexpected error during initialization: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    run_initialization()
