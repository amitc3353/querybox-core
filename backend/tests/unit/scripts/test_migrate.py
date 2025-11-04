"""
Unit Tests for Migration CLI Wrapper
Step 12.1: Database Automation Testing

Test Coverage:
- Alembic configuration loading
- Upgrade command execution
- Downgrade command with safety checks
- Dry-run mode for previewing SQL
- Migration history display
- Current version display
- Migration creation (autogenerate)
- Production safety prompts
- Error handling and recovery
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys
from alembic.config import Config

# Import the module under test
from scripts.migrate import (
    get_alembic_config,
    get_current_version,
    confirm_action,
    upgrade_migrations,
    downgrade_migrations,
    show_history,
    show_current,
    create_new_migration,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings with test database URL"""
    with patch('scripts.migrate.settings') as mock:
        mock.DATABASE_URL = "postgresql://test:test@localhost:5432/test_db"
        yield mock


@pytest.fixture
def mock_alembic_config():
    """Mock Alembic configuration"""
    mock = Mock(spec=Config)
    mock.set_main_option = Mock()
    return mock


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine"""
    mock = Mock()
    mock.connect.return_value.__enter__ = Mock()
    mock.connect.return_value.__exit__ = Mock(return_value=False)
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
    - Database URL set from environment
    """
    with patch('scripts.migrate.Path') as mock_path:
        mock_path.return_value.parent.parent = temp_alembic_ini.parent

        with patch('scripts.migrate.Config') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            result = get_alembic_config()

            mock_config.set_main_option.assert_called_once_with(
                "sqlalchemy.url",
                mock_settings.DATABASE_URL
            )


def test_get_alembic_config_missing_ini(tmp_path, mock_settings):
    """
    Test error when alembic.ini is missing

    Expected:
    - FileNotFoundError raised
    """
    with patch('scripts.migrate.Path') as mock_path:
        mock_path.return_value.parent.parent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError):
            get_alembic_config()


# ============================================================================
# TEST GET_CURRENT_VERSION
# ============================================================================

def test_get_current_version_with_version(mock_engine):
    """
    Test getting current version when migrations exist

    Expected:
    - Returns version string
    """
    mock_result = Mock()
    mock_result.fetchone.return_value = ("abc123def456",)

    mock_conn = Mock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.migrate.engine', mock_engine):
        version = get_current_version()

        assert version == "abc123def456"


def test_get_current_version_no_version(mock_engine):
    """
    Test getting version when no migrations applied

    Expected:
    - Returns "base"
    """
    mock_result = Mock()
    mock_result.fetchone.return_value = None

    mock_conn = Mock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.migrate.engine', mock_engine):
        version = get_current_version()

        assert version == "base"


def test_get_current_version_table_not_exists(mock_engine):
    """
    Test getting version when alembic_version table doesn't exist

    Expected:
    - Returns "base"
    - Exception caught
    """
    mock_conn = Mock()
    mock_conn.execute.side_effect = Exception("Table does not exist")
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)

    mock_engine.connect.return_value = mock_conn

    with patch('scripts.migrate.engine', mock_engine):
        version = get_current_version()

        assert version == "base"


# ============================================================================
# TEST CONFIRM_ACTION
# ============================================================================

def test_confirm_action_yes():
    """
    Test confirmation prompt with 'yes' input

    Expected:
    - Returns True
    """
    with patch('builtins.input', return_value='yes'):
        result = confirm_action("Are you sure?")
        assert result is True


def test_confirm_action_y():
    """
    Test confirmation prompt with 'y' input

    Expected:
    - Returns True
    """
    with patch('builtins.input', return_value='y'):
        result = confirm_action("Are you sure?")
        assert result is True


def test_confirm_action_no():
    """
    Test confirmation prompt with 'no' input

    Expected:
    - Returns False
    """
    with patch('builtins.input', return_value='no'):
        result = confirm_action("Are you sure?")
        assert result is False


def test_confirm_action_invalid():
    """
    Test confirmation prompt with invalid input

    Expected:
    - Returns False (default to safe option)
    """
    with patch('builtins.input', return_value='maybe'):
        result = confirm_action("Are you sure?")
        assert result is False


def test_confirm_action_case_insensitive():
    """
    Test confirmation is case insensitive

    Expected:
    - 'YES', 'Yes', 'yes' all return True
    """
    for input_val in ['YES', 'Yes', 'yes', 'Y']:
        with patch('builtins.input', return_value=input_val):
            result = confirm_action("Are you sure?")
            assert result is True


# ============================================================================
# TEST UPGRADE_MIGRATIONS
# ============================================================================

def test_upgrade_migrations_success(mock_alembic_config):
    """
    Test successful migration upgrade to head

    Expected:
    - Alembic upgrade command called
    - Version changes logged
    - Success message shown
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', side_effect=["base", "abc123"]):
            with patch('scripts.migrate.command') as mock_command:
                with patch('scripts.migrate.logger') as mock_logger:
                    upgrade_migrations()

                    mock_command.upgrade.assert_called_once_with(mock_alembic_config, "head")

                    # Verify logging
                    log_messages = [str(call) for call in mock_logger.info.call_args_list]
                    assert any("complete" in str(msg).lower() for msg in log_messages)


def test_upgrade_migrations_to_specific_version(mock_alembic_config):
    """
    Test upgrade to specific revision

    Expected:
    - Upgrade to specified revision, not head
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', side_effect=["base", "abc123"]):
            with patch('scripts.migrate.command') as mock_command:
                with patch('scripts.migrate.logger'):
                    upgrade_migrations(revision="abc123")

                    mock_command.upgrade.assert_called_once_with(mock_alembic_config, "abc123")


def test_upgrade_migrations_dry_run(mock_alembic_config):
    """
    Test dry-run mode generates SQL without executing

    Expected:
    - Upgrade called with sql=True
    - No actual database changes
    - SQL output logged
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.command') as mock_command:
            with patch('scripts.migrate.logger') as mock_logger:
                upgrade_migrations(dry_run=True)

                mock_command.upgrade.assert_called_once_with(mock_alembic_config, "head", sql=True)

                # Should log dry-run mode
                log_messages = [str(call) for call in mock_logger.info.call_args_list]
                assert any("dry-run" in str(msg).lower() for msg in log_messages)


def test_upgrade_migrations_failure(mock_alembic_config):
    """
    Test migration failure and error handling

    Expected:
    - SystemExit raised
    - Error logged
    - Rollback message shown
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="base"):
            with patch('scripts.migrate.command') as mock_command:
                mock_command.upgrade.side_effect = Exception("Migration failed")

                with patch('scripts.migrate.logger') as mock_logger:
                    with pytest.raises(SystemExit) as exc_info:
                        upgrade_migrations()

                    assert exc_info.value.code == 1

                    # Verify error logging
                    error_calls = [str(call) for call in mock_logger.error.call_args_list]
                    assert any("failed" in str(call).lower() for call in error_calls)


def test_upgrade_migrations_version_logging(mock_alembic_config):
    """
    Test that current and new versions are logged

    Expected:
    - Initial version logged
    - Final version logged
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', side_effect=["001_initial", "002_users"]):
            with patch('scripts.migrate.command'):
                with patch('scripts.migrate.logger') as mock_logger:
                    upgrade_migrations()

                    log_messages = [str(call) for call in mock_logger.info.call_args_list]
                    assert any("001_initial" in str(msg) for msg in log_messages)
                    assert any("002_users" in str(msg) for msg in log_messages)


# ============================================================================
# TEST DOWNGRADE_MIGRATIONS
# ============================================================================

def test_downgrade_migrations_success(mock_alembic_config):
    """
    Test successful migration downgrade

    Expected:
    - Alembic downgrade command called
    - Version changes logged
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', side_effect=["abc123", "base"]):
            with patch('scripts.migrate.command') as mock_command:
                with patch('scripts.migrate.settings') as mock_settings:
                    mock_settings.DATABASE_URL = "postgresql://test@localhost/test"

                    with patch('scripts.migrate.logger') as mock_logger:
                        downgrade_migrations("-1")

                        mock_command.downgrade.assert_called_once_with(mock_alembic_config, "-1")


def test_downgrade_migrations_dry_run(mock_alembic_config):
    """
    Test dry-run mode for downgrade

    Expected:
    - Downgrade called with sql=True
    - No actual rollback
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="abc123"):
            with patch('scripts.migrate.command') as mock_command:
                with patch('scripts.migrate.settings') as mock_settings:
                    mock_settings.DATABASE_URL = "postgresql://test@localhost/test"

                    with patch('scripts.migrate.logger'):
                        downgrade_migrations("-1", dry_run=True)

                        mock_command.downgrade.assert_called_once_with(mock_alembic_config, "-1", sql=True)


def test_downgrade_migrations_production_safety(mock_alembic_config):
    """
    Test production database safety check

    Expected:
    - Prompt shown for production databases
    - Downgrade cancelled if user declines
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="abc123"):
            with patch('scripts.migrate.settings') as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://user:pass@prod-db.com:5432/production"

                with patch('scripts.migrate.confirm_action', return_value=False):
                    with patch('scripts.migrate.command') as mock_command:
                        with patch('scripts.migrate.logger') as mock_logger:
                            downgrade_migrations("-1")

                            # Downgrade should NOT have been called
                            mock_command.downgrade.assert_not_called()

                            # Should log cancellation
                            log_messages = [str(call) for call in mock_logger.info.call_args_list]
                            assert any("cancelled" in str(msg).lower() for msg in log_messages)


def test_downgrade_migrations_production_confirmed(mock_alembic_config):
    """
    Test downgrade proceeds when user confirms in production

    Expected:
    - Downgrade executes after confirmation
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', side_effect=["abc123", "base"]):
            with patch('scripts.migrate.settings') as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://user:pass@prod.example.com:5432/production_db"

                with patch('scripts.migrate.confirm_action', return_value=True):
                    with patch('scripts.migrate.command') as mock_command:
                        with patch('scripts.migrate.logger'):
                            downgrade_migrations("-1")

                            # Downgrade should proceed
                            mock_command.downgrade.assert_called_once()


def test_downgrade_migrations_to_base(mock_alembic_config):
    """
    Test downgrade to base (remove all migrations)

    Expected:
    - Downgrade to "base" revision
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', side_effect=["abc123", "base"]):
            with patch('scripts.migrate.settings') as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test@localhost/test"

                with patch('scripts.migrate.command') as mock_command:
                    with patch('scripts.migrate.logger'):
                        downgrade_migrations("base")

                        mock_command.downgrade.assert_called_once_with(mock_alembic_config, "base")


def test_downgrade_migrations_failure(mock_alembic_config):
    """
    Test downgrade failure handling

    Expected:
    - SystemExit raised
    - Error logged
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="abc123"):
            with patch('scripts.migrate.settings') as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test@localhost/test"

                with patch('scripts.migrate.command') as mock_command:
                    mock_command.downgrade.side_effect = Exception("Downgrade failed")

                    with patch('scripts.migrate.logger') as mock_logger:
                        with pytest.raises(SystemExit) as exc_info:
                            downgrade_migrations("-1")

                        assert exc_info.value.code == 1

                        # Verify error logged
                        error_calls = [str(call) for call in mock_logger.error.call_args_list]
                        assert any("failed" in str(call).lower() for call in error_calls)


# ============================================================================
# TEST SHOW_HISTORY
# ============================================================================

def test_show_history_success(mock_alembic_config):
    """
    Test migration history display

    Expected:
    - Alembic history command called
    - Verbose mode enabled
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.command') as mock_command:
            with patch('scripts.migrate.logger'):
                show_history()

                mock_command.history.assert_called_once_with(mock_alembic_config, verbose=True)


# ============================================================================
# TEST SHOW_CURRENT
# ============================================================================

def test_show_current_success(mock_alembic_config):
    """
    Test current version display

    Expected:
    - Current version retrieved
    - Database URL logged (masked)
    - Alembic current command called
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="abc123"):
            with patch('scripts.migrate.settings') as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/test_db"

                with patch('scripts.migrate.command') as mock_command:
                    with patch('scripts.migrate.logger') as mock_logger:
                        show_current()

                        # Verify version was logged
                        log_messages = [str(call) for call in mock_logger.info.call_args_list]
                        assert any("abc123" in str(msg) for msg in log_messages)

                        # Verify Alembic command called
                        mock_command.current.assert_called_once()


def test_show_current_base_version(mock_alembic_config):
    """
    Test showing current when at base (no migrations)

    Expected:
    - "base" version displayed
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="base"):
            with patch('scripts.migrate.settings') as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test@localhost/test"

                with patch('scripts.migrate.command'):
                    with patch('scripts.migrate.logger') as mock_logger:
                        show_current()

                        log_messages = [str(call) for call in mock_logger.info.call_args_list]
                        assert any("base" in str(msg) for msg in log_messages)


# ============================================================================
# TEST CREATE_NEW_MIGRATION
# ============================================================================

def test_create_new_migration_autogenerate(mock_alembic_config):
    """
    Test creating new migration with autogenerate

    Expected:
    - Alembic revision command called
    - autogenerate=True
    - Success message logged
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.command') as mock_command:
            with patch('scripts.migrate.logger') as mock_logger:
                create_new_migration("Add user table")

                mock_command.revision.assert_called_once_with(
                    mock_alembic_config,
                    message="Add user table",
                    autogenerate=True
                )

                # Verify success message
                log_messages = [str(call) for call in mock_logger.info.call_args_list]
                assert any("created" in str(msg).lower() for msg in log_messages)


def test_create_new_migration_manual(mock_alembic_config):
    """
    Test creating empty migration template

    Expected:
    - autogenerate=False
    - Empty migration created
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.command') as mock_command:
            with patch('scripts.migrate.logger'):
                create_new_migration("Custom migration", autogenerate=False)

                mock_command.revision.assert_called_once_with(
                    mock_alembic_config,
                    message="Custom migration",
                    autogenerate=False
                )


def test_create_new_migration_reminder(mock_alembic_config):
    """
    Test that creation logs reminder to review migration

    Expected:
    - Reminder to review generated file
    - Location of migration file mentioned
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.command'):
            with patch('scripts.migrate.logger') as mock_logger:
                create_new_migration("Test migration")

                log_messages = [str(call) for call in mock_logger.info.call_args_list]
                assert any("review" in str(msg).lower() for msg in log_messages)
                assert any("alembic/versions" in str(msg) for msg in log_messages)


# ============================================================================
# TEST MAIN CLI INTEGRATION
# ============================================================================

def test_main_upgrade_command(mock_settings):
    """
    Test main CLI with upgrade command

    Expected:
    - upgrade_migrations called
    - Default revision=head
    """
    with patch('scripts.migrate.upgrade_migrations') as mock_upgrade:
        with patch('sys.argv', ['migrate.py', 'upgrade']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            mock_upgrade.assert_called_once()


def test_main_upgrade_with_dry_run(mock_settings):
    """
    Test main CLI with upgrade --dry-run

    Expected:
    - upgrade_migrations called with dry_run=True
    """
    with patch('scripts.migrate.upgrade_migrations') as mock_upgrade:
        with patch('sys.argv', ['migrate.py', 'upgrade', '--dry-run']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            # Check that dry_run was passed
            call_args = mock_upgrade.call_args
            assert call_args[1]['dry_run'] is True


def test_main_downgrade_command(mock_settings):
    """
    Test main CLI with downgrade command

    Expected:
    - downgrade_migrations called
    - Revision specified
    """
    with patch('scripts.migrate.downgrade_migrations') as mock_downgrade:
        with patch('sys.argv', ['migrate.py', 'downgrade', '-1']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            mock_downgrade.assert_called_once()
            assert mock_downgrade.call_args[1]['revision'] == "-1"


def test_main_history_command(mock_settings):
    """
    Test main CLI with history command

    Expected:
    - show_history called
    """
    with patch('scripts.migrate.show_history') as mock_history:
        with patch('sys.argv', ['migrate.py', 'history']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            mock_history.assert_called_once()


def test_main_current_command(mock_settings):
    """
    Test main CLI with current command

    Expected:
    - show_current called
    """
    with patch('scripts.migrate.show_current') as mock_current:
        with patch('sys.argv', ['migrate.py', 'current']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            mock_current.assert_called_once()


def test_main_dry_run_shortcut(mock_settings):
    """
    Test main CLI with dry-run command (shortcut for upgrade --dry-run head)

    Expected:
    - upgrade_migrations called with dry_run=True
    """
    with patch('scripts.migrate.upgrade_migrations') as mock_upgrade:
        with patch('sys.argv', ['migrate.py', 'dry-run']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            call_args = mock_upgrade.call_args
            assert call_args[1]['revision'] == "head"
            assert call_args[1]['dry_run'] is True


def test_main_create_command(mock_settings):
    """
    Test main CLI with create command

    Expected:
    - create_new_migration called
    - Message passed
    """
    with patch('scripts.migrate.create_new_migration') as mock_create:
        with patch('sys.argv', ['migrate.py', 'create', 'Add users table']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            mock_create.assert_called_once()
            assert mock_create.call_args[1]['message'] == "Add users table"


def test_main_create_no_autogenerate(mock_settings):
    """
    Test main CLI with create --no-autogenerate

    Expected:
    - create_new_migration called with autogenerate=False
    """
    with patch('scripts.migrate.create_new_migration') as mock_create:
        with patch('sys.argv', ['migrate.py', 'create', 'Manual migration', '--no-autogenerate']):
            from scripts.migrate import main

            try:
                main()
            except SystemExit:
                pass

            call_args = mock_create.call_args
            assert call_args[1]['autogenerate'] is False


def test_main_no_command(mock_settings):
    """
    Test main CLI without command

    Expected:
    - Help printed
    - Exit with code 1
    """
    with patch('sys.argv', ['migrate.py']):
        with pytest.raises(SystemExit) as exc_info:
            from scripts.migrate import main
            main()

        assert exc_info.value.code == 1


# ============================================================================
# TEST ERROR EDGE CASES
# ============================================================================

def test_upgrade_with_network_error(mock_alembic_config):
    """
    Test upgrade handling network/connection errors

    Expected:
    - Error caught and logged
    - Helpful error message
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="base"):
            with patch('scripts.migrate.command') as mock_command:
                from sqlalchemy.exc import OperationalError
                mock_command.upgrade.side_effect = OperationalError("Connection refused", None, None)

                with patch('scripts.migrate.logger') as mock_logger:
                    with pytest.raises(SystemExit):
                        upgrade_migrations()

                    # Should log connection error
                    error_calls = [str(call) for call in mock_logger.error.call_args_list]
                    assert any("failed" in str(call).lower() for call in error_calls)


def test_downgrade_version_not_found(mock_alembic_config):
    """
    Test downgrade to non-existent revision

    Expected:
    - Error caught
    - Helpful error message about invalid revision
    """
    with patch('scripts.migrate.get_alembic_config', return_value=mock_alembic_config):
        with patch('scripts.migrate.get_current_version', return_value="abc123"):
            with patch('scripts.migrate.settings') as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test@localhost/test"

                with patch('scripts.migrate.command') as mock_command:
                    mock_command.downgrade.side_effect = Exception("Revision not found: xyz999")

                    with patch('scripts.migrate.logger') as mock_logger:
                        with pytest.raises(SystemExit):
                            downgrade_migrations("xyz999")

                        error_calls = [str(call) for call in mock_logger.error.call_args_list]
                        assert any("failed" in str(call).lower() for call in error_calls)
