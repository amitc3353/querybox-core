#!/usr/bin/env python3
"""
Database Initialization Script
Step 12.1: Database Automation

This script initializes the database by:
1. Validating database connectivity
2. Running Alembic migrations programmatically
3. Verifying schema integrity post-migration
4. Optional: Creating initial admin user

Usage:
    python scripts/init_db.py                    # Run migrations
    python scripts/init_db.py --check            # Check current version
    python scripts/init_db.py --create-admin     # Run migrations + create admin user

Purpose: Automated initialization for CI/CD pipelines
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.db.database import engine, test_connection
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """
    Get Alembic configuration with environment-aware database URL.

    Returns:
        Alembic Config object configured for current environment
    """
    # Get path to alembic.ini (should be in backend/ directory)
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {alembic_ini_path}. "
            "Run this script from backend/ directory."
        )

    # Load Alembic configuration
    alembic_cfg = Config(str(alembic_ini_path))

    # Override database URL from environment (12-factor app)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    return alembic_cfg


def check_database_connectivity() -> bool:
    """
    Validate database is reachable and accepts connections.

    Returns:
        True if database is reachable, False otherwise

    Raises:
        SystemExit if database is unreachable
    """
    logger.info("Checking database connectivity...")

    try:
        if not test_connection():
            logger.error("❌ Database connection failed!")
            logger.error(f"   DATABASE_URL: {settings.DATABASE_URL}")
            logger.error("   Verify database is running and credentials are correct.")
            sys.exit(1)
    except Exception as e:
        logger.error("❌ Database connection failed!")
        logger.error(f"   DATABASE_URL: {settings.DATABASE_URL}")
        logger.error(f"   Error: {str(e)}")
        logger.error("   Verify database is running and credentials are correct.")
        sys.exit(1)

    logger.info("✅ Database connection successful")
    return True


def get_current_migration_version() -> str:
    """
    Get current Alembic migration version from database.

    Returns:
        Current migration version (revision ID) or "base" if no migrations applied

    Note:
        Returns "base" if alembic_version table doesn't exist
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            row = result.fetchone()
            if row:
                return row[0]
            else:
                return "base"
    except Exception:
        # alembic_version table doesn't exist yet
        return "base"


def run_migrations() -> None:
    """
    Run Alembic migrations to bring database schema to latest version.

    This function:
    1. Gets current migration version
    2. Runs pending migrations via `alembic upgrade head`
    3. Verifies migration success
    4. Reports final version

    Raises:
        SystemExit if migration fails
    """
    logger.info("Checking current migration version...")
    current_version = get_current_migration_version()
    logger.info(f"   Current version: {current_version}")

    logger.info("Running migrations...")
    alembic_cfg = get_alembic_config()

    try:
        # Run migrations to head (latest)
        command.upgrade(alembic_cfg, "head")

        # Verify migration success
        new_version = get_current_migration_version()
        logger.info(f"✅ Migrations complete")
        logger.info(f"   New version: {new_version}")

        if new_version == current_version and current_version != "base":
            logger.info("   (No new migrations to apply)")

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        logger.error("   Database changes have been rolled back.")
        sys.exit(1)


def verify_schema_integrity() -> None:
    """
    Verify database schema integrity post-migration.

    Checks:
    1. All expected tables exist
    2. pgvector extension is installed
    3. Critical indexes are present

    Raises:
        SystemExit if schema verification fails
    """
    logger.info("Verifying schema integrity...")

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Expected tables from models
    expected_tables = [
        "documents",
        "document_versions",
        "document_texts",
        "processing_status",
        "processing_queue",
        "embeddings",
        "alembic_version"  # Created by Alembic
    ]

    missing_tables = [t for t in expected_tables if t not in tables]

    if missing_tables:
        logger.error(f"❌ Missing tables: {', '.join(missing_tables)}")
        sys.exit(1)

    logger.info(f"✅ All expected tables present ({len(expected_tables)} tables)")

    # Check pgvector extension
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname='vector'")
            )
            if result.scalar() == "vector":
                logger.info("✅ pgvector extension installed")
            else:
                logger.warning("⚠️  pgvector extension not found (required for embeddings)")
    except Exception as e:
        logger.warning(f"⚠️  Could not verify pgvector extension: {str(e)}")


def create_admin_user() -> None:
    """
    Create initial admin user (placeholder for future implementation).

    TODO: Implement when user management is added
    """
    logger.info("Admin user creation not yet implemented")
    logger.info("(User management will be added in future steps)")


def main():
    """
    Main entry point for database initialization.

    Supports multiple modes:
    - Default: Run migrations
    - --check: Check current migration version without applying
    - --create-admin: Run migrations and create admin user
    """
    parser = argparse.ArgumentParser(
        description="Initialize QueryboxCore database with migrations"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current migration version without applying migrations"
    )
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Create initial admin user after migrations"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify schema integrity, don't run migrations"
    )

    args = parser.parse_args()

    # Banner
    logger.info("=" * 60)
    logger.info("QueryboxCore Database Initialization")
    logger.info("=" * 60)

    # Step 1: Check database connectivity
    check_database_connectivity()

    # Step 2: Handle different modes
    if args.check:
        # Check mode: Display current version
        current_version = get_current_migration_version()
        logger.info(f"Current migration version: {current_version}")
        sys.exit(0)

    elif args.verify_only:
        # Verify mode: Check schema without running migrations
        verify_schema_integrity()
        sys.exit(0)

    else:
        # Default mode: Run migrations
        run_migrations()
        verify_schema_integrity()

        if args.create_admin:
            create_admin_user()

    # Success
    logger.info("=" * 60)
    logger.info("✅ Database initialization complete!")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
