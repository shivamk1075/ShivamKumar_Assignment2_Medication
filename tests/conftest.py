"""
Pytest configuration and fixtures for the test suite.
"""
import pytest
from pathlib import Path
import sys


test_dir = Path(__file__).parent
project_root = test_dir.parent
sys.path.insert(0, str(project_root))
