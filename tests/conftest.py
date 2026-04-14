"""Shared test fixtures."""
import pytest

from odoo_views_dsl import _registry


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the global registry before and after each test."""
    _registry.clear()
    yield
    _registry.clear()
