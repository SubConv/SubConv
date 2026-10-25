"""Shared fixtures for the SubConv converter test suite.

Inserts the repository root into ``sys.path`` so ``import subconv``
works without installing the package.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from subconv.converter.registry import NameRegistry  # noqa: E402


@pytest.fixture()
def registry() -> NameRegistry:
    """Return a fresh name registry (no names registered yet)."""
    return NameRegistry()
