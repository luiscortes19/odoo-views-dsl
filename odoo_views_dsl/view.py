# Stub — implementation planned
"""View decorators: @view.list, @view.form, @view.form.extend"""


class _ViewRegistry:
    """Collects view definitions for later compilation to XML."""

    def list(self, id=None, model=None, string=None, domain=None, decorations=None):
        """Decorator for list (tree) views."""
        def decorator(fn):
            fn._odoo_view = {
                'type': 'list',
                'id': id,
                'model': model,
                'string': string,
                'domain': domain,
                'decorations': decorations or {},
            }
            return fn
        return decorator

    def form(self, id=None, model=None, string=None, inherit=None):
        """Decorator for form views."""
        def decorator(fn):
            fn._odoo_view = {
                'type': 'form',
                'id': id,
                'model': model,
                'string': string,
                'inherit': inherit,
            }
            return fn
        return decorator


view = _ViewRegistry()
