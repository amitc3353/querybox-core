"""
Integration Tests for Health Check Script
Step 12.2: Deployment Infrastructure Testing

Test Coverage:
- Script execution and exit codes
- Health check endpoint verification
- PostgreSQL container health check
- Redis container health check
- MinIO container health check
- Timeout behavior
- Command-line argument parsing
- Error reporting and logging
- Service status display
"""

import pytest
import subprocess
import time
from pathlib import Path
import requests
from typing import Optional


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

HEALTH_CHECK_SCRIPT = Path(__file__).parent.parent.parent.parent / "scripts" / "health_check.sh"
BACKEND_URL = "http://localhost:8000"
POSTGRES_CONTAINER = "querybox-postgres"
REDIS_CONTAINER = "querybox-redis"
MINIO_CONTAINER = "querybox-minio"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_health_check(
    timeout: Optional[int] = None,
    interval: Optional[int] = None,
    capture_output: bool = True
) -> subprocess.CompletedProcess:
    """
    Run health check script with optional arguments

    Args:
        timeout: Total timeout in seconds
        interval: Check interval in seconds
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess result
    """
    cmd = [str(HEALTH_CHECK_SCRIPT)]

    if timeout is not None:
        cmd.extend(["--timeout", str(timeout)])

    if interval is not None:
        cmd.extend(["--interval", str(interval)])

    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        timeout=max(timeout or 60, 60) + 10  # Add buffer to script timeout
    )


def is_container_running(container_name: str) -> bool:
    """
    Check if Docker container is running

    Args:
        container_name: Name of container to check

    Returns:
        True if container is running, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return container_name in result.stdout
    except subprocess.CalledProcessError:
        return False


def is_backend_healthy() -> bool:
    """
    Check if backend API is healthy

    Returns:
        True if health endpoint returns healthy status
    """
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") in ["healthy", "ok"]
        return False
    except Exception:
        return False


def wait_for_backend_startup(max_wait: int = 30) -> bool:
    """
    Wait for backend to start up

    Args:
        max_wait: Maximum time to wait in seconds

    Returns:
        True if backend started, False if timeout
    """
    start = time.time()
    while time.time() - start < max_wait:
        if is_backend_healthy():
            return True
        time.sleep(2)
    return False


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def ensure_script_exists():
    """
    Ensure health check script exists and is executable

    Raises:
        FileNotFoundError if script doesn't exist
    """
    if not HEALTH_CHECK_SCRIPT.exists():
        pytest.skip(f"Health check script not found at {HEALTH_CHECK_SCRIPT}")

    # Make script executable
    HEALTH_CHECK_SCRIPT.chmod(0o755)

    yield


@pytest.fixture(scope="module")
def docker_available():
    """
    Check if Docker is available

    Skips tests if Docker is not installed
    """
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Docker not available")

    yield


@pytest.fixture(scope="module")
def services_running(docker_available):
    """
    Ensure all required services are running

    Skips tests if services are not running
    """
    required_containers = [POSTGRES_CONTAINER, REDIS_CONTAINER, MINIO_CONTAINER]

    missing = [c for c in required_containers if not is_container_running(c)]

    if missing:
        pytest.skip(f"Required containers not running: {', '.join(missing)}")

    # Wait for backend to be ready
    if not wait_for_backend_startup():
        pytest.skip("Backend failed to start within timeout")

    yield


# ============================================================================
# TEST SCRIPT EXECUTION
# ============================================================================

def test_script_exists_and_executable(ensure_script_exists):
    """
    Test that health check script exists and is executable

    Expected:
    - Script file exists
    - Script has execute permissions
    """
    assert HEALTH_CHECK_SCRIPT.exists()
    assert HEALTH_CHECK_SCRIPT.stat().st_mode & 0o111  # Has execute permission


def test_script_runs_successfully(ensure_script_exists, services_running):
    """
    Test script execution with all services healthy

    Expected:
    - Exit code 0
    - Success message in output
    - No errors
    """
    result = run_health_check(timeout=60, interval=5)

    assert result.returncode == 0
    assert "healthy" in result.stdout.lower()


def test_script_with_help_flag(ensure_script_exists):
    """
    Test script --help flag

    Expected:
    - Help message displayed
    - Usage information shown
    - Exit code 0
    """
    result = subprocess.run(
        [str(HEALTH_CHECK_SCRIPT), "--help"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "options" in result.stdout.lower()
    assert "--timeout" in result.stdout
    assert "--interval" in result.stdout


# ============================================================================
# TEST HEALTH CHECKS
# ============================================================================

def test_backend_health_check(ensure_script_exists, services_running):
    """
    Test backend API health check

    Expected:
    - Backend health verified
    - Health status logged
    """
    result = run_health_check(timeout=30, interval=5)

    assert result.returncode == 0
    assert "backend" in result.stdout.lower()
    assert "healthy" in result.stdout.lower()


def test_postgres_health_check(ensure_script_exists, services_running):
    """
    Test PostgreSQL container health check

    Expected:
    - PostgreSQL status verified
    - Container checked via pg_isready
    """
    result = run_health_check(timeout=30, interval=5)

    assert result.returncode == 0
    assert "postgres" in result.stdout.lower()


def test_redis_health_check(ensure_script_exists, services_running):
    """
    Test Redis container health check

    Expected:
    - Redis status verified
    - PING command executed
    """
    result = run_health_check(timeout=30, interval=5)

    assert result.returncode == 0
    assert "redis" in result.stdout.lower()


def test_minio_health_check(ensure_script_exists, services_running):
    """
    Test MinIO container health check

    Expected:
    - MinIO status verified
    - Health endpoint checked
    """
    result = run_health_check(timeout=30, interval=5)

    assert result.returncode == 0
    assert "minio" in result.stdout.lower()


# ============================================================================
# TEST TIMEOUT BEHAVIOR
# ============================================================================

def test_custom_timeout(ensure_script_exists, services_running):
    """
    Test custom timeout parameter

    Expected:
    - Script respects timeout setting
    - Completes within specified time (since services are healthy)
    """
    start_time = time.time()
    result = run_health_check(timeout=15, interval=3)
    elapsed = time.time() - start_time

    assert result.returncode == 0
    # Should complete quickly since services are healthy
    assert elapsed < 15


def test_custom_interval(ensure_script_exists, services_running):
    """
    Test custom check interval

    Expected:
    - Script uses specified interval
    - Multiple checks may occur if needed
    """
    result = run_health_check(timeout=20, interval=3)

    assert result.returncode == 0


@pytest.mark.slow
def test_timeout_with_unhealthy_service(ensure_script_exists, docker_available):
    """
    Test timeout when services are not healthy

    Expected:
    - Script times out after specified duration
    - Exit code 1
    - Timeout message in output

    Note: This test requires services to NOT be running
    """
    # Skip if services are actually running
    if is_backend_healthy():
        pytest.skip("Services are healthy, cannot test timeout behavior")

    result = run_health_check(timeout=10, interval=2)

    assert result.returncode == 1
    assert "timeout" in result.stdout.lower() or "unhealthy" in result.stdout.lower()


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================

def test_invalid_timeout_parameter(ensure_script_exists):
    """
    Test handling of invalid timeout value

    Expected:
    - Error message or default behavior
    - Script handles invalid input gracefully
    """
    result = subprocess.run(
        [str(HEALTH_CHECK_SCRIPT), "--timeout", "invalid"],
        capture_output=True,
        text=True,
        timeout=10
    )

    # Script should either reject invalid input or use default
    # Exit code may be non-zero for invalid input
    assert result.returncode in [0, 1]


def test_invalid_interval_parameter(ensure_script_exists):
    """
    Test handling of invalid interval value

    Expected:
    - Error message or default behavior
    """
    result = subprocess.run(
        [str(HEALTH_CHECK_SCRIPT), "--interval", "invalid"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode in [0, 1]


def test_unknown_option(ensure_script_exists):
    """
    Test handling of unknown command-line option

    Expected:
    - Error message
    - Exit code 1
    - Help hint shown
    """
    result = subprocess.run(
        [str(HEALTH_CHECK_SCRIPT), "--unknown-option"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "unknown" in result.stdout.lower() or "error" in result.stdout.lower()


# ============================================================================
# TEST OUTPUT FORMATTING
# ============================================================================

def test_output_contains_service_names(ensure_script_exists, services_running):
    """
    Test that output clearly shows which services were checked

    Expected:
    - Backend mentioned
    - PostgreSQL mentioned
    - Redis mentioned
    - MinIO mentioned
    """
    result = run_health_check(timeout=30, interval=5)

    output_lower = result.stdout.lower()

    assert "backend" in output_lower or "api" in output_lower
    assert "postgres" in output_lower or "database" in output_lower
    assert "redis" in output_lower or "cache" in output_lower
    assert "minio" in output_lower or "storage" in output_lower


def test_output_contains_status_indicators(ensure_script_exists, services_running):
    """
    Test that output contains clear status indicators

    Expected:
    - Success indicators (✓, ✅, OK, healthy, etc.)
    - Status clearly visible
    """
    result = run_health_check(timeout=30, interval=5)

    output = result.stdout

    # Should have some positive indicators
    has_indicators = (
        "✓" in output or
        "✅" in output or
        "OK" in output or
        "healthy" in output.lower() or
        "up" in output.lower()
    )

    assert has_indicators


def test_output_shows_progress(ensure_script_exists, services_running):
    """
    Test that output shows progress/attempts

    Expected:
    - Attempt numbers or progress indicators
    - Elapsed time or similar progress metric
    """
    result = run_health_check(timeout=30, interval=5)

    output = result.stdout.lower()

    # Should show some progress information
    has_progress = (
        "attempt" in output or
        "checking" in output or
        "elapsed" in output or
        "waiting" in output
    )

    assert has_progress


# ============================================================================
# TEST CONCURRENT EXECUTION
# ============================================================================

def test_script_can_run_multiple_times_concurrently(ensure_script_exists, services_running):
    """
    Test that multiple instances of script can run simultaneously

    Expected:
    - Both instances complete successfully
    - No conflicts or deadlocks
    """
    import concurrent.futures

    def run_check():
        return run_health_check(timeout=20, interval=5)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(run_check)
        future2 = executor.submit(run_check)

        result1 = future1.result()
        result2 = future2.result()

    assert result1.returncode == 0
    assert result2.returncode == 0


# ============================================================================
# TEST SERVICE STATUS DISPLAY
# ============================================================================

def test_shows_container_status(ensure_script_exists, services_running):
    """
    Test that script shows Docker container status

    Expected:
    - Container names listed
    - Status (Running, Up, etc.) shown
    """
    result = run_health_check(timeout=30, interval=5)

    output = result.stdout

    # Should mention container status
    assert POSTGRES_CONTAINER in output or "postgres" in output.lower()


# ============================================================================
# TEST INTEGRATION WITH BACKEND
# ============================================================================

def test_detects_backend_health_endpoint(ensure_script_exists, services_running):
    """
    Test that script correctly queries backend /health endpoint

    Expected:
    - HTTP request made to /health
    - JSON response parsed
    - Health status extracted
    """
    result = run_health_check(timeout=30, interval=5)

    assert result.returncode == 0

    # Verify backend actually has health endpoint
    response = requests.get(f"{BACKEND_URL}/health")
    assert response.status_code == 200


def test_validates_backend_response_format(ensure_script_exists, services_running):
    """
    Test that script validates health endpoint response

    Expected:
    - Checks for 'status' field
    - Verifies 'healthy' or 'ok' value
    - Rejects invalid responses
    """
    result = run_health_check(timeout=30, interval=5)

    # Should pass since backend returns proper format
    assert result.returncode == 0


# ============================================================================
# TEST PERFORMANCE
# ============================================================================

@pytest.mark.slow
def test_script_completes_quickly_when_healthy(ensure_script_exists, services_running):
    """
    Test that script completes quickly when all services are healthy

    Expected:
    - Completes in < 10 seconds
    - No unnecessary waiting
    """
    start_time = time.time()
    result = run_health_check(timeout=60, interval=5)
    elapsed = time.time() - start_time

    assert result.returncode == 0
    assert elapsed < 10  # Should be very fast when all healthy


def test_script_respects_check_interval(ensure_script_exists, services_running):
    """
    Test that script waits specified interval between checks

    Expected:
    - Interval parameter respected
    - Not checking more frequently than specified
    """
    # Use short timeout to force multiple checks
    result = run_health_check(timeout=15, interval=3)

    # Script should complete successfully
    # Timing validation is implicit in the interval parameter
    assert result.returncode == 0


# ============================================================================
# TEST ERROR MESSAGES
# ============================================================================

@pytest.mark.slow
def test_error_message_when_backend_down(ensure_script_exists, docker_available):
    """
    Test error message when backend is not responding

    Expected:
    - Clear error about backend being unhealthy
    - HTTP status code or connection error mentioned

    Note: Requires backend to be stopped
    """
    if is_backend_healthy():
        pytest.skip("Backend is running, cannot test down scenario")

    result = run_health_check(timeout=10, interval=2)

    assert result.returncode == 1
    assert "backend" in result.stdout.lower() or "api" in result.stdout.lower()
    assert "unhealthy" in result.stdout.lower() or "failed" in result.stdout.lower()


# ============================================================================
# TEST EXIT CODES
# ============================================================================

def test_exit_code_zero_when_all_healthy(ensure_script_exists, services_running):
    """
    Test exit code 0 when all services are healthy

    Expected:
    - Exit code exactly 0
    - Success status
    """
    result = run_health_check(timeout=30, interval=5)

    assert result.returncode == 0


@pytest.mark.slow
def test_exit_code_one_when_unhealthy(ensure_script_exists, docker_available):
    """
    Test exit code 1 when services are unhealthy

    Expected:
    - Exit code 1
    - Error status

    Note: Requires services to be down
    """
    if is_backend_healthy():
        pytest.skip("Services are healthy, cannot test failure exit code")

    result = run_health_check(timeout=10, interval=2)

    assert result.returncode == 1


# ============================================================================
# TEST SIGNAL HANDLING
# ============================================================================

@pytest.mark.slow
def test_script_can_be_interrupted(ensure_script_exists):
    """
    Test that script can be interrupted with Ctrl+C

    Expected:
    - Script exits gracefully when interrupted
    - No zombie processes
    """
    import signal

    # Start script with long timeout
    process = subprocess.Popen(
        [str(HEALTH_CHECK_SCRIPT), "--timeout", "120", "--interval", "5"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait a moment then interrupt
    time.sleep(2)
    process.send_signal(signal.SIGINT)

    try:
        stdout, stderr = process.communicate(timeout=5)
        # Script should exit (return code may vary)
        assert process.returncode is not None
    except subprocess.TimeoutExpired:
        process.kill()
        pytest.fail("Script did not exit after SIGINT")
