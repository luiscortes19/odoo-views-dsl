# Stub — implementation planned
"""Action decorators: @action.window"""


class _ActionRegistry:
    """Collects action definitions for later compilation to XML."""

    def window(self, id=None, model=None, string=None, domain=None, default_filters=None):
        """Decorator for window actions (act_window)."""
        def decorator(fn):
            fn._odoo_action = {
                'type': 'window',
                'id': id,
                'model': model,
                'string': string,
                'domain': domain,
                'default_filters': default_filters or {},
            }
            return fn
        return decorator


action = _ActionRegistry()
