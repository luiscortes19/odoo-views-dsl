# Stub — implementation planned
"""Settings page decorator: @settings.page"""


class _SettingsRegistry:
    """Collects settings page definitions for later compilation to XML."""

    def page(self, module_key, title):
        """Decorator for res.config.settings pages."""
        def decorator(fn):
            fn._odoo_settings = {
                'module_key': module_key,
                'title': title,
            }
            return fn
        return decorator


settings = _SettingsRegistry()
