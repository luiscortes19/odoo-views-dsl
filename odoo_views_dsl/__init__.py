# odoo-views-dsl — Python-native DSL for Odoo views
"""
Write Odoo views, menus, and actions in Python.
Compile to standard XML. Never touch <record>/<field> XML again.
"""

__version__ = '0.1.0'

from .view import view
from .menu import menu
from .action import action
from .settings import settings

__all__ = ['view', 'menu', 'action', 'settings']
