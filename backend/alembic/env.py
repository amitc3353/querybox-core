"""
Alembic Environment Configuration for QueryboxCore
Step 12.1: Database Automation

This module bridges Alembic's migration framework with QueryboxCore's
SQLAlchemy models. It handles:
- Model metadata import from app.models
- Database connection from environment variables
- Transaction management with automatic rollback on failure
- Both online (connected) and offline (SQL generation) modes
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add parent directory to Python path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import application models for metadata
# This automatically imports all models via __init__.py
from app.db.database import Base
from app.models import (
    Document,
    DocumentVersion,
    DocumentText,
    ProcessingStatus,
    Embedding,
    ProcessingQueue
)

# Alembic Config object provides access to values in .ini file
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# This allows Alembic to detect model changes automatically
target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    Use case: Generate SQL migration scripts without connecting to database
    Command: alembic upgrade --sql head > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (connected to database).

    This is the standard migration mode used in development and production.

    Critical features:
    - Transaction wrapping for atomic migrations
    - Automatic rollback on failure
    - Connection pooling disabled (migration is one-time operation)
    - Environment variable configuration (12-factor app)
    - Type and default comparison enabled for comprehensive change detection
    """

    # Override database URL from environment variable if set
    # This allows different environments (dev/staging/prod) to use different databases
    # Priority: DATABASE_URL env var > alembic.ini value
    configuration = config.get_section(config.config_ini_section)
    database_url = os.getenv(
        "DATABASE_URL",
        configuration.get("sqlalchemy.url", "postgresql://postgres:postgres@localhost:5432/querybox")
    )
    configuration["sqlalchemy.url"] = database_url

    # Create engine with no pooling
    # Rationale: Migrations don't benefit from connection reuse since they're one-time operations
    # NullPool prevents connection pool exhaustion during long-running migrations
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Critical: Avoid connection pool exhaustion
    )

    with connectable.connect() as connection:
        # Configure migration context
        context.configure(
            connection=connection,
            target_metadata=target_metadata,

            # Comparison settings (detect more changes)
            compare_type=True,              # Detect column type changes (e.g., Integer -> BigInteger)
            compare_server_default=True,    # Detect default value changes

            # Schema settings
            include_schemas=False,           # Single schema (public)
            version_table="alembic_version", # Track current migration version

            # Render settings
            render_as_batch=False,           # Don't use batch mode (PostgreSQL supports ALTER well)
        )

        # Run migration within transaction
        # Automatic COMMIT on success, ROLLBACK on any exception
        with context.begin_transaction():
            try:
                context.run_migrations()
                # Migration successful - changes will be committed
            except Exception as e:
                # Migration failed - changes will be rolled back
                # Re-raise to propagate error to caller
                print(f"Migration failed: {str(e)}")
                raise


# Determine which mode to run based on context
# Online mode is default (used by `alembic upgrade head`)
# Offline mode is used for SQL generation (`alembic upgrade --sql head`)
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
