#!/usr/bin/env python3
"""
End-to-End Test Runner for QueryBox

This script runs the complete E2E integration test suite and provides
detailed output about the pipeline status.

Usage:
    python backend/scripts/run_e2e_tests.py
    python backend/scripts/run_e2e_tests.py --verbose
    python backend/scripts/run_e2e_tests.py --quick  # Skip slow tests
"""
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def check_services():
    """
    Check if required services are running

    Returns tuple of (all_healthy, service_status)
    """
    print("=" * 80)
    print("CHECKING SERVICES")
    print("=" * 80)

    service_status = {
        "postgres": False,
        "redis": False,
        "ollama": False
    }

    # Check PostgreSQL
    try:
        import psycopg2
        from app.core.config import settings

        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        conn.close()
        service_status["postgres"] = True
        print("✓ PostgreSQL: Running")
    except Exception as e:
        print(f"✗ PostgreSQL: Not available ({e})")

    # Check Redis (optional)
    try:
        import redis
        from app.core.config import settings

        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        r.ping()
        service_status["redis"] = True
        print("✓ Redis: Running")
    except Exception as e:
        print(f"⚠ Redis: Not available ({e}) - Tests will continue")

    # Check Ollama (optional for answer generation)
    try:
        import requests
        from app.core.config import settings

        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            service_status["ollama"] = True
            print("✓ Ollama: Running")
        else:
            print("⚠ Ollama: Not healthy - Answer generation tests will be skipped")
    except Exception as e:
        print(f"⚠ Ollama: Not available ({e}) - Answer generation tests will be skipped")

    print()

    # Check if critical services are running
    critical_services = ["postgres"]
    all_critical_healthy = all(service_status[s] for s in critical_services)

    return all_critical_healthy, service_status


def run_e2e_tests(verbose: bool = False, quick: bool = False):
    """
    Run the E2E test suite

    Args:
        verbose: Show detailed test output
        quick: Skip slow tests
    """
    print("=" * 80)
    print("RUNNING END-TO-END INTEGRATION TESTS")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Build pytest command
    cmd = [
        "pytest",
        "backend/tests/integration/test_e2e_pipeline.py",
        "-v" if verbose else "-v",
        "--tb=short",
        "-m", "integration"
    ]

    if quick:
        cmd.extend(["-m", "not slow"])

    # Add coverage if requested
    if "--cov" in sys.argv:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:backend/htmlcov"
        ])

    print(f"Command: {' '.join(cmd)}")
    print()

    # Run tests
    try:
        result = subprocess.run(cmd, cwd=Path.cwd())
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nError running tests: {e}")
        return 1


def print_summary(return_code: int, service_status: dict):
    """Print test summary"""
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if return_code == 0:
        print("✓ ALL E2E TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")

    print()
    print("Service Status:")
    for service, status in service_status.items():
        icon = "✓" if status else "✗"
        print(f"  {icon} {service}: {'Running' if status else 'Not available'}")

    print()
    print("Next steps:")
    if return_code == 0:
        print("  • All tests passed! The complete pipeline is working.")
        print("  • You can now test with real documents via API")
    else:
        print("  • Review test output above for failures")
        print("  • Check service logs: docker-compose logs -f")
        print("  • Ensure all required services are running")

    print("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run QueryBox E2E Integration Tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed test output"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Skip slow tests"
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip service health checks"
    )

    args = parser.parse_args()

    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "QueryBox E2E Test Runner" + " " * 34 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Check services
    if not args.skip_checks:
        all_healthy, service_status = check_services()

        if not all_healthy:
            print("✗ ERROR: Critical services are not running")
            print()
            print("Please start services with:")
            print("  docker-compose up -d postgres redis ollama")
            print()
            return 1
    else:
        service_status = {}

    # Run tests
    return_code = run_e2e_tests(
        verbose=args.verbose,
        quick=args.quick
    )

    # Print summary
    print_summary(return_code, service_status)

    return return_code


if __name__ == "__main__":
    sys.exit(main())
