"""Shared test fixtures for MAS-FRO backend tests."""

import sys
import os

# Ensure app modules are importable from tests without installing the package.
# This replaces the per-file sys.path.append pattern used in existing tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
