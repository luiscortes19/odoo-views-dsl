"""Settings page decorator: ``@settings.page``.

Generates an inherited view of ``base.res_config_settings_view_form``
that adds an ``<app>`` section with ``<block>``/``<setting>`` elements.
"""
from __future__ import annotations

from . import _registry


class _SettingsRegistry:
    """Registry for ``@settings.page`` definitions."""

    def page(self, *, id: str, module: str, string: str = '', **kwargs):
        """Decorator for ``res.config.settings`` pages.

        Parameters
        ----------
        id : str
            XML ID for the inherited view record.
        module : str
            Technical module name (used for ``<app name="...">``)
            and for the settings action context.
        string : str
            App display name in the Settings sidebar.

        Example::

            @settings.page(
                id='res_config_settings_my_module',
                module='my_module',
                string='My Module',
            )
            def my_settings(s):
                with s.block('API Connection'):
                    with s.setting('API Endpoint', help='Your API config.'):
                        s.field('api_url', readonly=True)
                        s.field('api_key', password=True)
        """
        def decorator(fn):
            entry = {
                'type': 'settings', 'fn': fn, 'id': id,
                'module': module, 'string': string,
                **kwargs,
            }
            _registry.settings.append(entry)
            fn._odoo_settings = entry
            return fn
        return decorator


settings = _SettingsRegistry()
