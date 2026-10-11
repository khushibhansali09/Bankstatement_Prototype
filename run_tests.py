#!/usr/bin/env python3
"""Run the test suite without needing to remember the pytest incantation."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    import pytest  # noqa: F401
except ImportError:
    print("pytest is not installed. Install it with:\n  pip install pytest")
    raise SystemExit(1)

raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")]))
