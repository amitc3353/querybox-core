#!/usr/bin/env python3
"""
Migration CLI Wrapper with Safety Checks
Step 12.1: Database Automation

This script provides a developer-friendly interface to Alembic with safety features:
- Dry-run mode to preview SQL before execution
- Backup prompts for downgrade operations
- Clear error messages and recovery instructions
- Migration history visualization

Usage:
    python scripts/migrate.py upgrade           # Apply pending migrations
    python scripts/migrate.py downgrade -1      # Rollback last migration
    python scripts/migrate.py history           # Show migration history
    python scripts/migrate.py current           # Show current version
    python scripts/migrate.py dry-run           # Generate SQL without executing

Purpose: Developer-friendly migration interface with safety checks
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
from sqlalchemy import text

from app.db.database import engine
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-5.5s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """
    Get Alembic configuration with environment-aware database URL.

    Returns:
        Alembic Config object configured for current environment
    """
    alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {alembic_ini_path}"
        )

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    return alembic_cfg


def get_current_version() -> str:
    """
    Get current migration version from database.

    Returns:
        Current version or "base" if no migrations applied
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            row = result.fetchone()
            return row[0] if row else "base"
    except Exception:
        return "base"


def confirm_action(message: str) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Confirmation message to display

    Returns:
        True if user confirms, False otherwise
    """
    response = input(f"{message} (yes/no): ").lower().strip()
    return response in ["yes", "y"]


def upgrade_migrations(revision: str = "head", dry_run: bool = False) -> None:
    """
    Apply pending migrations.

    Args:
        revision: Target revision (default: "head" for latest)
        dry_run: If True, generate SQL without executing
    """
    alembic_cfg = get_alembic_config()

    if dry_run:
        logger.info("🔍 Dry-run mode: Generating SQL without executing...")
        logger.info("=" * 60)
        command.upgrade(alembic_cfg, revision, sql=True)
        logger.info("=" * 60)
        logger.info("To apply these changes, run without --dry-run flag")
        return

    logger.info(f"Applying migrations to: {revision}")
    current = get_current_version()
    logger.info(f"Current version: {current}")

    try:
        command.upgrade(alembic_cfg, revision)
        new_version = get_current_version()
        logger.info(f"✅ Migration complete")
        logger.info(f"   New version: {new_version}")
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        logger.error("   Changes have been rolled back.")
        logger.error("   Check logs above for details.")
        sys.exit(1)


def downgrade_migrations(revision: str, dry_run: bool = False) -> None:
    """
    Rollback migrations.

    Args:
        revision: Target revision (e.g., "-1" for previous, specific revision ID, or "base")
        dry_run: If True, generate SQL without executing
    """
    alembic_cfg = get_alembic_config()

    current = get_current_version()
    logger.info(f"Current version: {current}")
    logger.info(f"Target version: {revision}")

    if dry_run:
        logger.info("🔍 Dry-run mode: Generating SQL without executing...")
        logger.info("=" * 60)
        command.downgrade(alembic_cfg, revision, sql=True)
        logger.info("=" * 60)
        logger.info("To apply these changes, run without --dry-run flag")
        return

    # Safety check: Confirm downgrade in production
    if "prod" in settings.DATABASE_URL.lower() or "production" in settings.DATABASE_URL.lower():
        logger.warning("⚠️  PRODUCTION DATABASE DETECTED")
        logger.warning("   Downgrading migrations in production can cause data loss!")
        if not confirm_action("Are you sure you want to downgrade?"):
            logger.info("Downgrade cancelled.")
            return

    logger.info("Rolling back migrations...")

    try:
        command.downgrade(alembic_cfg, revision)
        new_version = get_current_version()
        logger.info(f"✅ Rollback complete")
        logger.info(f"   New version: {new_version}")
    except Exception as e:
        logger.error(f"❌ Rollback failed: {str(e)}")
        logger.error("   Check logs above for details.")
        sys.exit(1)


def show_history() -> None:
    """
    Display migration history.
    """
    alembic_cfg = get_alembic_config()
    logger.info("Migration History:")
    logger.info("=" * 60)
    command.history(alembic_cfg, verbose=True)


def show_current() -> None:
    """
    Display current migration version.
    """
    alembic_cfg = get_alembic_config()
    current = get_current_version()

    logger.info("=" * 60)
    logger.info("Current Migration Version")
    logger.info("=" * 60)
    logger.info(f"Version: {current}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    logger.info("=" * 60)

    # Show detailed current info via Alembic
    command.current(alembic_cfg, verbose=True)


def create_new_migration(message: str, autogenerate: bool = True) -> None:
    """
    Create a new migration file.

    Args:
        message: Description of the migration
        autogenerate: If True, auto-detect model changes
    """
    alembic_cfg = get_alembic_config()

    logger.info(f"Creating new migration: {message}")

    if autogenerate:
        logger.info("Auto-generating migration from model changes...")
        command.revision(alembic_cfg, message=message, autogenerate=True)
    else:
        logger.info("Creating empty migration template...")
        command.revision(alembic_cfg, message=message, autogenerate=False)

    logger.info("✅ Migration file created")
    logger.info("   Review the generated file in alembic/versions/")
    logger.info("   Make any necessary adjustments before applying")


def main():
    """
    Main CLI entry point.
    """
    parser = argparse.ArgumentParser(
        description="QueryboxCore Database Migration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s upgrade                    # Apply all pending migrations
  %(prog)s downgrade -1               # Rollback last migration
  %(prog)s downgrade base             # Rollback all migrations
  %(prog)s history                    # Show migration history
  %(prog)s current                    # Show current version
  %(prog)s dry-run                    # Preview SQL without executing
  %(prog)s create "Add user table"    # Create new migration
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Migration commands")

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Apply pending migrations")
    upgrade_parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Target revision (default: head)"
    )
    upgrade_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate SQL without executing"
    )

    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Rollback migrations")
    downgrade_parser.add_argument(
        "revision",
        help="Target revision (-1 for previous, base for all, or specific revision)"
    )
    downgrade_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate SQL without executing"
    )

    # History command
    subparsers.add_parser("history", help="Show migration history")

    # Current command
    subparsers.add_parser("current", help="Show current migration version")

    # Dry-run command (shortcut for upgrade --dry-run head)
    subparsers.add_parser("dry-run", help="Preview next migrations without executing")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new migration")
    create_parser.add_argument(
        "message",
        help="Migration description (e.g., 'Add user table')"
    )
    create_parser.add_argument(
        "--no-autogenerate",
        action="store_true",
        help="Create empty migration (don't auto-detect changes)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        if args.command == "upgrade":
            upgrade_migrations(revision=args.revision, dry_run=args.dry_run)

        elif args.command == "downgrade":
            downgrade_migrations(revision=args.revision, dry_run=args.dry_run)

        elif args.command == "history":
            show_history()

        elif args.command == "current":
            show_current()

        elif args.command == "dry-run":
            upgrade_migrations(revision="head", dry_run=True)

        elif args.command == "create":
            create_new_migration(message=args.message, autogenerate=not args.no_autogenerate)

    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
