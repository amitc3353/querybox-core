"""
Unit Tests for Database Initialization Script
Step 12.1: Database Automation Testing

Test Coverage:
- Database connectivity validation
- Alembic configuration loading
- Migration version checking
- Migration execution
- Schema integrity verification
- Error handling and recovery
- Command-line argument parsing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from alembic.config import Config

# Import the module under test
from scripts.init_db import (
    get_alembic_config,
    check_database_connectivity,
    get_current_migration_version,
    run_migrations,
    verify_schema_integrity,
    create_admin_user,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings with test database URL"""
    with patch('scripts.init_db.settings') as mock:
        mock.DATABASE_URL = "postgresql://test:test@localhost:5432/test_db"
        yield mock


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine"""
    mock = Mock()
    mock.connect.return_value.__enter__ = Mock()
    mock.connect.return_value.__exit__ = Mock(return_value=False)
    return mock


@pytest.fixture
def mock_alembic_config():
    """Mock Alembic configuration"""
    mock = Mock(spec=Config)
    mock.set_main_option = Mock()
    return mock


@pytest.fixture
def temp_alembic_ini(tmp_path):
    """Create temporary alembic.ini file"""
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()

    alembic_ini = backend_dir / "alembic.ini"
    alembic_ini.write_text("""
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://user:pass@localhost/dbname

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic
""")

    return alembic_ini


# ============================================================================
# TEST GET_ALEMBIC_CONFIG
# ============================================================================

def test_get_alembic_config_success(temp_alembic_ini, mock_settings):
    """
    Test successful Alembic configuration loading

    Expected:
    - Config object created
    - Database URL set from settings
    - No exceptions raised
    """
    with patch('scripts.init_db.Path') as mock_path:
        mock_path.return_value.parent.parent = temp_alembic_ini.parent

        # Mock Config to avoid actual Alembic initialization
        with patch('scripts.init_db.Config') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            result = get_alembic_config()

            # Verify Config was created with correct path
            assert mock_config_class.called

            # Verify database URL was set
            mock_config.set_main_option.assert_called_once_with(
                "sqlalchemy.url",
                mock_settings.DATABASE_URL
            )


def test_get_alembic_config_missing_ini(tmp_path, mock_settings):
    """
    Test error handling when alembic.ini is missing

    Expected:
    - FileNotFoundError raised
    - Error message mentions alembic.ini location
    """
    with patch('scripts.init_db.Path') as mock_path:
        # Point to non-existent directory
        mock_path.return_value.parent.parent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError) as exc_info:
            get_alembic_config()

        assert "alembic.ini not found" in str(exc_info.value)


def test_get_alembic_config_uses_environment_url(temp_alembic_ini, mock_settings):
    """
    Test that database URL is taken from environment settings

    Expected:
    - Config uses DATABASE_URL from settings, not hardcoded value
    """
    custom_url = "postgresql://custom:pass@custom-host:5432/custom_db"
    mock_settings.DATABASE_URL = custom_url

    with patch('scripts.init_db.Path') as mock_path:
        mock_path.return_value.parent.parent = temp_alembic_ini.parent

        with patch('scripts.init_db.Config') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            get_alembic_config()

            # Verify custom URL was used
            mock_config.set_main_option.assert_called_with(
                "sqlalchemy.url",
                custom_url
            )


# ============================================================================
# TEST CHECK_DATABASE_CONNECTIVITY
# ============================================================================

def test_check_database_connectivity_success(mock_settings):
    """
    Test successful database connectivity check

    Expected:
    - Returns True
    - No exceptions raised
    - Logs success message
    """
    with patch('scripts.init_db.test_connection', return_value=True):
        with patch('scripts.init_db.logger') as mock_logger:
            result = check_database_connectivity()

            assert result is True
            mock_logger.info.assert_any_call("Checking database connectivity...")
            mock_logger.info.assert_any_call("✅ Database connection successful")


def test_check_database_connectivity_failure(mock_settings):
    """
    Test failed database connectivity check

    Expected:
    - SystemExit raised
    - Error message logged
    - Database URL included in error
    """
    with patch('scripts.init_db.test_connection', return_value=False):
        with patch('scripts.init_db.logger') as mock_logger:
            with pytest.raises(SystemExit) as exc_info:
                check_database_connectivity()

            assert exc_info.value.code == 1

            # Verify error logging
            mock_logger.error.assert_any_call("❌ Database connection failed!")

            # Check that DATABASE_URL was logged
            log_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any(mock_settings.DATABASE_URL in str(call) for call in log_calls)


def test_check_database_connectivity_with_exception(mock_settings):
    """
    Test database connectivity check when exception occurs

    Expected:
    - SystemExit raised
    - Exception handled gracefully
    """
    with patch('scripts.init_db.test_connection', side_effect=OperationalError("Connection refused", None, None)):
        with pytest.raises(SystemExit):
            check_database_connectivity()


# ============================================================================
# TEST GET_CURRENT_MIGRATION_VERSION
# ============================================================================

def test_get_current_migration_version_with_version(mock_engine):
    """
    Test getting current migration version when migrations exist

    Expected:
    - Returns version string
    - Queries alembic_version table
    """
    mock_result = Mock()
    mock_result.fetchone.return_value = ("abc123def456",)

    mock_conn = Mock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.init_db.engine', mock_engine):
        version = get_current_migration_version()

        assert version == "abc123def456"
        mock_conn.execute.assert_called_once()


def test_get_current_migration_version_no_version(mock_engine):
    """
    Test getting current migration version when no migrations applied

    Expected:
    - Returns "base"
    - No exception raised
    """
    mock_result = Mock()
    mock_result.fetchone.return_value = None

    mock_conn = Mock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.init_db.engine', mock_engine):
        version = get_current_migration_version()

        assert version == "base"


def test_get_current_migration_version_table_not_exists(mock_engine):
    """
    Test getting version when alembic_version table doesn't exist

    Expected:
    - Returns "base"
    - Exception caught and handled
    """
    mock_conn = Mock()
    mock_conn.execute.side_effect = Exception("Table does not exist")
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.init_db.engine', mock_engine):
        version = get_current_migration_version()

        assert version == "base"


# ============================================================================
# TEST RUN_MIGRATIONS
# ============================================================================

def test_run_migrations_success(mock_alembic_config):
    """
    Test successful migration execution

    Expected:
    - Migrations run to head
    - Success logged
    - Version checked before and after
    """
    with patch('scripts.init_db.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.init_db.get_current_migration_version', side_effect=["base", "abc123"]):
            with patch('scripts.init_db.command') as mock_command:
                with patch('scripts.init_db.logger') as mock_logger:
                    run_migrations()

                    # Verify upgrade command was called
                    mock_command.upgrade.assert_called_once_with(mock_alembic_config, "head")

                    # Verify success logging
                    assert any("complete" in str(call).lower() for call in mock_logger.info.call_args_list)


def test_run_migrations_already_up_to_date(mock_alembic_config):
    """
    Test migrations when already at latest version

    Expected:
    - Upgrade still called (idempotent)
    - Message indicating no new migrations
    """
    with patch('scripts.init_db.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.init_db.get_current_migration_version', return_value="abc123"):
            with patch('scripts.init_db.command') as mock_command:
                with patch('scripts.init_db.logger') as mock_logger:
                    run_migrations()

                    mock_command.upgrade.assert_called_once()

                    # Should log that no new migrations were applied
                    log_messages = [str(call) for call in mock_logger.info.call_args_list]
                    assert any("No new migrations" in str(msg) for msg in log_messages)


def test_run_migrations_failure(mock_alembic_config):
    """
    Test migration failure and rollback

    Expected:
    - SystemExit raised
    - Error logged
    - Rollback message shown
    """
    with patch('scripts.init_db.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.init_db.get_current_migration_version', return_value="base"):
            with patch('scripts.init_db.command') as mock_command:
                mock_command.upgrade.side_effect = Exception("Migration failed: syntax error")

                with patch('scripts.init_db.logger') as mock_logger:
                    with pytest.raises(SystemExit) as exc_info:
                        run_migrations()

                    assert exc_info.value.code == 1

                    # Verify error logging
                    error_calls = [str(call) for call in mock_logger.error.call_args_list]
                    assert any("Migration failed" in str(call) for call in error_calls)
                    assert any("rolled back" in str(call).lower() for call in error_calls)


def test_run_migrations_version_progression(mock_alembic_config):
    """
    Test that migration version progresses correctly

    Expected:
    - Initial version logged
    - Final version logged
    - Version changes from old to new
    """
    old_version = "001_initial"
    new_version = "002_add_users"

    with patch('scripts.init_db.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.init_db.get_current_migration_version', side_effect=[old_version, new_version]):
            with patch('scripts.init_db.command'):
                with patch('scripts.init_db.logger') as mock_logger:
                    run_migrations()

                    # Verify both versions were logged
                    log_messages = [str(call) for call in mock_logger.info.call_args_list]
                    assert any(old_version in str(msg) for msg in log_messages)
                    assert any(new_version in str(msg) for msg in log_messages)


# ============================================================================
# TEST VERIFY_SCHEMA_INTEGRITY
# ============================================================================

def test_verify_schema_integrity_success(mock_engine):
    """
    Test successful schema integrity verification

    Expected:
    - All tables checked
    - pgvector extension checked
    - Success logged
    """
    mock_inspector = Mock()
    mock_inspector.get_table_names.return_value = [
        "documents",
        "document_versions",
        "document_texts",
        "processing_status",
        "processing_queue",
        "embeddings",
        "alembic_version"
    ]

    mock_result = Mock()
    mock_result.scalar.return_value = "vector"

    mock_conn = Mock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.init_db.engine', mock_engine):
        with patch('scripts.init_db.inspect', return_value=mock_inspector):
            with patch('scripts.init_db.logger') as mock_logger:
                verify_schema_integrity()

                # Verify success messages
                log_messages = [str(call) for call in mock_logger.info.call_args_list]
                assert any("All expected tables present" in str(msg) for msg in log_messages)
                assert any("pgvector extension installed" in str(msg) for msg in log_messages)


def test_verify_schema_integrity_missing_tables(mock_engine):
    """
    Test schema verification when tables are missing

    Expected:
    - SystemExit raised
    - Missing tables listed
    - Error logged
    """
    mock_inspector = Mock()
    mock_inspector.get_table_names.return_value = [
        "documents",
        "alembic_version"
        # Missing: document_versions, document_texts, etc.
    ]

    with patch('scripts.init_db.engine', mock_engine):
        with patch('scripts.init_db.inspect', return_value=mock_inspector):
            with patch('scripts.init_db.logger') as mock_logger:
                with pytest.raises(SystemExit) as exc_info:
                    verify_schema_integrity()

                assert exc_info.value.code == 1

                # Verify error logging
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                assert any("Missing tables" in str(call) for call in error_calls)


def test_verify_schema_integrity_missing_pgvector(mock_engine):
    """
    Test schema verification when pgvector extension is missing

    Expected:
    - Warning logged (not fatal)
    - Continues execution
    """
    mock_inspector = Mock()
    mock_inspector.get_table_names.return_value = [
        "documents",
        "document_versions",
        "document_texts",
        "processing_status",
        "processing_queue",
        "embeddings",
        "alembic_version"
    ]

    mock_result = Mock()
    mock_result.scalar.return_value = None  # Extension not found

    mock_conn = Mock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.init_db.engine', mock_engine):
        with patch('scripts.init_db.inspect', return_value=mock_inspector):
            with patch('scripts.init_db.logger') as mock_logger:
                verify_schema_integrity()  # Should not raise

                # Verify warning logged
                warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                assert any("pgvector extension not found" in str(call) for call in warning_calls)


def test_verify_schema_integrity_extension_check_error(mock_engine):
    """
    Test schema verification when extension check fails

    Expected:
    - Warning logged
    - Error caught and handled gracefully
    """
    mock_inspector = Mock()
    mock_inspector.get_table_names.return_value = [
        "documents",
        "document_versions",
        "document_texts",
        "processing_status",
        "processing_queue",
        "embeddings",
        "alembic_version"
    ]

    mock_conn = Mock()
    mock_conn.execute.side_effect = Exception("Permission denied")
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.init_db.engine', mock_engine):
        with patch('scripts.init_db.inspect', return_value=mock_inspector):
            with patch('scripts.init_db.logger') as mock_logger:
                verify_schema_integrity()  # Should not raise

                # Verify warning logged
                warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                assert any("Could not verify pgvector" in str(call) for call in warning_calls)


# ============================================================================
# TEST CREATE_ADMIN_USER
# ============================================================================

def test_create_admin_user_not_implemented():
    """
    Test admin user creation (currently not implemented)

    Expected:
    - Function runs without error
    - Logs that feature is not yet implemented
    """
    with patch('scripts.init_db.logger') as mock_logger:
        create_admin_user()

        # Verify placeholder message
        log_messages = [str(call) for call in mock_logger.info.call_args_list]
        assert any("not yet implemented" in str(msg).lower() for msg in log_messages)


# ============================================================================
# TEST MAIN FUNCTION INTEGRATION
# ============================================================================

def test_main_default_mode(mock_settings):
    """
    Test main function in default mode (run migrations)

    Expected:
    - Connectivity checked
    - Migrations run
    - Schema verified
    - Success banner shown
    """
    with patch('scripts.init_db.check_database_connectivity', return_value=True):
        with patch('scripts.init_db.run_migrations'):
            with patch('scripts.init_db.verify_schema_integrity'):
                with patch('scripts.init_db.logger') as mock_logger:
                    with patch('sys.argv', ['init_db.py']):
                        from scripts.init_db import main

                        with pytest.raises(SystemExit) as exc_info:
                            main()

                        # Should exit with success code
                        assert exc_info.value.code == 0

                        # Verify success messages
                        log_messages = [str(call) for call in mock_logger.info.call_args_list]
                        assert any("initialization complete" in str(msg).lower() for msg in log_messages)


def test_main_check_mode(mock_settings):
    """
    Test main function with --check flag

    Expected:
    - Only version checked
    - No migrations run
    - Exit with code 0
    """
    with patch('scripts.init_db.check_database_connectivity', return_value=True):
        with patch('scripts.init_db.get_current_migration_version', return_value="abc123"):
            with patch('scripts.init_db.run_migrations') as mock_run:
                with patch('sys.argv', ['init_db.py', '--check']):
                    from scripts.init_db import main

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 0

                    # Migrations should NOT have been run
                    mock_run.assert_not_called()


def test_main_verify_only_mode(mock_settings):
    """
    Test main function with --verify-only flag

    Expected:
    - Only schema verified
    - No migrations run
    """
    with patch('scripts.init_db.check_database_connectivity', return_value=True):
        with patch('scripts.init_db.verify_schema_integrity'):
            with patch('scripts.init_db.run_migrations') as mock_run:
                with patch('sys.argv', ['init_db.py', '--verify-only']):
                    from scripts.init_db import main

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 0

                    # Migrations should NOT have been run
                    mock_run.assert_not_called()


def test_main_create_admin_mode(mock_settings):
    """
    Test main function with --create-admin flag

    Expected:
    - Migrations run
    - Admin user creation attempted
    """
    with patch('scripts.init_db.check_database_connectivity', return_value=True):
        with patch('scripts.init_db.run_migrations'):
            with patch('scripts.init_db.verify_schema_integrity'):
                with patch('scripts.init_db.create_admin_user') as mock_admin:
                    with patch('sys.argv', ['init_db.py', '--create-admin']):
                        from scripts.init_db import main

                        with pytest.raises(SystemExit) as exc_info:
                            main()

                        assert exc_info.value.code == 0

                        # Admin user creation should have been called
                        mock_admin.assert_called_once()


# ============================================================================
# TEST ERROR RECOVERY
# ============================================================================

def test_connectivity_failure_stops_execution(mock_settings):
    """
    Test that failed connectivity check prevents further execution

    Expected:
    - Migrations not attempted
    - Exit immediately after connectivity failure
    """
    with patch('scripts.init_db.check_database_connectivity', side_effect=SystemExit(1)):
        with patch('scripts.init_db.run_migrations') as mock_run:
            with pytest.raises(SystemExit):
                from scripts.init_db import main
                main()

            # Migrations should never be attempted
            mock_run.assert_not_called()


def test_migration_failure_stops_verification(mock_settings):
    """
    Test that failed migrations prevent schema verification

    Expected:
    - Verification not attempted after migration failure
    """
    with patch('scripts.init_db.check_database_connectivity', return_value=True):
        with patch('scripts.init_db.run_migrations', side_effect=SystemExit(1)):
            with patch('scripts.init_db.verify_schema_integrity') as mock_verify:
                with pytest.raises(SystemExit):
                    from scripts.init_db import main
                    main()

                # Verification should never be attempted
                mock_verify.assert_not_called()
