# Unit Tests for Step 12 Deployment Scripts

This directory contains comprehensive unit tests for the deployment automation scripts added in Step 12.

## Test Files

### `test_init_db.py`
Tests for database initialization script (`backend/scripts/init_db.py`)

**Coverage:**
- ✅ Alembic configuration loading
- ✅ Database connectivity validation
- ✅ Migration version checking
- ✅ Migration execution (upgrade to head)
- ✅ Schema integrity verification
- ✅ Error handling and recovery
- ✅ Command-line argument parsing (--check, --verify-only, --create-admin)
- ✅ Production safety checks

**Key Test Scenarios:**
- Successful migration from base to latest version
- Migration failure and rollback
- Missing alembic.ini file handling
- Database connection failures
- Missing table detection
- pgvector extension verification

### `test_migrate.py`
Tests for migration CLI wrapper (`backend/scripts/migrate.py`)

**Coverage:**
- ✅ Migration upgrade commands
- ✅ Migration downgrade with safety prompts
- ✅ Dry-run mode (SQL preview without execution)
- ✅ Migration history display
- ✅ Current version display
- ✅ New migration creation (autogenerate)
- ✅ Production database safety checks
- ✅ Error handling and recovery
- ✅ All CLI commands (upgrade, downgrade, history, current, dry-run, create)

**Key Test Scenarios:**
- Upgrade to head and specific revisions
- Downgrade with confirmation for production databases
- Dry-run mode generates SQL without executing
- Safety prompt prevents accidental production downgrades
- Invalid revision handling
- Network/connection error recovery

### `test_seed_demo.py`
Tests for demo data seeder (`backend/scripts/seed_demo.py`)

**Coverage:**
- ✅ Document content generation (5 document types)
- ✅ Demo data seeder initialization
- ✅ Document upload with retry logic (exponential backoff)
- ✅ Processing status monitoring
- ✅ Search verification
- ✅ Error recovery and partial failures
- ✅ Command-line argument parsing (--count, --skip-verify)
- ✅ Progress tracking and logging

**Key Test Scenarios:**
- All 5 document generators produce unique, substantial content
- Upload with retry logic (3 attempts with exponential backoff)
- Concurrent upload handling
- Processing status polling with timeout
- Search verification after seeding
- Partial failure handling (some uploads fail, others succeed)

## Running the Tests

### Run All Script Tests
```bash
cd backend
pytest tests/unit/scripts/ -v
```

### Run Individual Test Files
```bash
# Test database initialization
pytest tests/unit/scripts/test_init_db.py -v

# Test migration CLI
pytest tests/unit/scripts/test_migrate.py -v

# Test demo data seeder
pytest tests/unit/scripts/test_seed_demo.py -v
```

### Run Specific Test Functions
```bash
# Test specific scenario
pytest tests/unit/scripts/test_init_db.py::test_run_migrations_success -v

# Test migration dry-run
pytest tests/unit/scripts/test_migrate.py::test_upgrade_migrations_dry_run -v

# Test document generation
pytest tests/unit/scripts/test_seed_demo.py::test_generate_technical_pdf_content -v
```

### Run with Coverage Report
```bash
pytest tests/unit/scripts/ --cov=scripts --cov-report=html --cov-report=term
```

### Run Only Fast Tests (Skip Slow Tests)
```bash
pytest tests/unit/scripts/ -m "not slow"
```

## Test Dependencies

These tests use the following mocking and testing libraries:
- `pytest` - Test framework
- `unittest.mock` - Mocking framework (Python standard library)
- `pytest-cov` - Coverage reporting (optional)

No additional dependencies required beyond what's in `requirements.txt`.

## Test Patterns Used

### 1. Mock External Dependencies
All tests mock external dependencies to ensure unit isolation:
- Database connections mocked via `mock_engine`
- Alembic commands mocked via `patch('scripts.X.command')`
- HTTP requests mocked via `patch('scripts.seed_demo.requests')`
- File system operations use temporary directories

### 2. Fixtures for Reusable Setup
Common test setup is extracted into pytest fixtures:
```python
@pytest.fixture
def mock_settings():
    """Mock settings with test database URL"""
    with patch('scripts.init_db.settings') as mock:
        mock.DATABASE_URL = "postgresql://test:test@localhost:5432/test_db"
        yield mock
```

### 3. Comprehensive Error Testing
Each script has tests for:
- Success paths (happy path)
- Error conditions (network failures, missing files, etc.)
- Edge cases (empty input, invalid parameters)
- Recovery mechanisms (retries, rollbacks)

### 4. Command-Line Interface Testing
CLI argument parsing is tested using `patch('sys.argv')`:
```python
with patch('sys.argv', ['migrate.py', 'upgrade', '--dry-run']):
    from scripts.migrate import main
    main()
```

## Coverage Metrics

Target coverage: **>90% for all scripts**

Current coverage (run `pytest --cov` to see latest):
- `init_db.py`: >95%
- `migrate.py`: >95%
- `seed_demo.py`: >90%

## Adding New Tests

When adding new functionality to scripts:

1. **Add corresponding test function** following naming convention `test_<feature>_<scenario>`
2. **Mock external dependencies** - never hit real databases, APIs, or file systems
3. **Test both success and failure paths**
4. **Use descriptive docstrings** explaining what is being tested and expected behavior
5. **Follow existing patterns** - look at similar tests for guidance

Example:
```python
def test_new_feature_success(mock_settings):
    """
    Test new feature under normal conditions

    Expected:
    - Feature executes successfully
    - Correct return value
    - Side effects verified
    """
    with patch('scripts.module.external_call') as mock_call:
        result = function_under_test()

        assert result == expected_value
        mock_call.assert_called_once()
```

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError`, ensure you're running from the `backend/` directory:
```bash
cd backend
pytest tests/unit/scripts/
```

### Mock Not Found
If mocks aren't working, verify the import path:
```python
# Wrong: patch('module.function')
# Right: patch('scripts.init_db.function')
```

### Test Timeout
Some tests may timeout if retry logic is activated. Adjust retry settings or increase test timeout:
```python
@pytest.mark.timeout(60)  # 60 second timeout
def test_with_retries():
    ...
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines without external dependencies:
- No database required (all mocked)
- No Docker required (unless running integration tests)
- No network access required
- Fast execution (<30 seconds for all unit tests)

Add to your CI pipeline:
```yaml
# .github/workflows/test.yml
- name: Run Script Unit Tests
  run: |
    cd backend
    pytest tests/unit/scripts/ -v --cov=scripts --cov-report=xml
```

## Related Documentation

- [Step 12 Technical Documentation](../../../docs/technical/step-12-quick-wins-demo-foundation.md)
- [Integration Tests](../../integration/test_health_check_script.py)
- [Contributing Guidelines](../../../../CONTRIBUTING.md)

## Questions or Issues?

If you encounter issues with these tests:
1. Check the test output for specific error messages
2. Review the script being tested for recent changes
3. Verify mock configuration matches actual implementation
4. Open an issue with test failure details
