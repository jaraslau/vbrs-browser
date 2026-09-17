"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def es_client() -> MagicMock:
    """Return a mock Elasticsearch client for repository/index tests."""
    return MagicMock()