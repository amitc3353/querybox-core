"""
Pytest configuration for root-level tests.
Adds backend directory to Python path for imports.
"""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))
