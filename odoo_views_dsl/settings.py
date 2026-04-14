"""Settings page decorator: ``@settings.page``.

.. note:: Settings compilation is Phase 4.  The decorator captures
   the definition but does not yet emit XML.
"""
from __future__ import annotations


class _SettingsRegistry:
    """Collects settings page definitions for later compilation to XML."""

    def page(self, module_key: str, title: str):
        """Decorator for ``res.config.settings`` pages.

        Example::

            @settings.page('warehouse_module', 'Warehouse')
            def warehouse_settings(s):
                with s.block('API Connection'):
                    s.field('api_url', 'API URL')
        """
        def decorator(fn):
            fn._odoo_settings = {
                'module_key': module_key,
                'title': title,
            }
            return fn
        return decorator


settings = _SettingsRegistry()
