"""Global registry for DSL definitions.

Decorators register view/action/menu definitions here at import time.
The compiler reads and processes them during compilation.
"""
from __future__ import annotations

views: list[dict] = []
actions: list[dict] = []
menus: list[dict] = []
settings: list[dict] = []


def clear():
    """Clear all registered definitions. Called before each compilation run."""
    views.clear()
    actions.clear()
    menus.clear()
    settings.clear()
