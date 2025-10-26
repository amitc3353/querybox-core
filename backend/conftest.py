"""
Pytest configuration for backend tests.
Adds the backend directory to Python path to enable imports from 'app'.
"""
import sys
from pathlib import Path

# Add backend directory (current directory) to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
