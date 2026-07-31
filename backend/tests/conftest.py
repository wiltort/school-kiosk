"""Pytest configuration — adds src/ to Python path."""

import sys
from pathlib import Path

# Add src/ to sys.path so imports like `from core.config import ...` work
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
