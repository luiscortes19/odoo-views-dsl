"""View decorators: ``@view.list``, ``@view.form``, ``@view.form.extend``,
``@view.list.extend``."""
from __future__ import annotations

from . import _registry


class _ListDecorator:
    """Callable descriptor for ``@view.list(...)`` and ``@view.list.extend(...)``."""

    def __call__(self, *, id: str, model: str, string: str = '',
                 domain=None, decorations: dict | None = None,
                 editable: str | None = None, **kwargs):
        """Decorator for standalone list views."""
        def decorator(fn):
            entry = {
                'type': 'list', 'fn': fn, 'id': id, 'model': model,
                'string': string, 'domain': domain,
                'decorations': decorations or {},
                'editable': editable, **kwargs,
            }
            _registry.views.append(entry)
            fn._odoo_view = entry
            return fn
        return decorator

    def extend(self, *, id: str, inherit: str, model: str,
               priority: int | None = None, **kwargs):
        """Decorator for inherited list views.

        ``model`` is **required** — Odoo needs it to validate
        the view's fields against the ORM model.

        Example::

            @view.list.extend(
                id='partner_list_custom',
                inherit='base.view_partner_list',
                model='res.partner',
            )
            def extend_partner_list(v):
                v.after('name', v.make_field('custom_field', 'Custom'))
        """
        def decorator(fn):
            entry = {
                'type': 'list', 'subtype': 'extend', 'fn': fn,
                'id': id, 'model': model, 'inherit': inherit,
                'priority': priority, **kwargs,
            }
            _registry.views.append(entry)
            fn._odoo_view = entry
            return fn
        return decorator


class _FormDecorator:
    """Callable descriptor for ``@view.form(...)`` and ``@view.form.extend(...)``."""

    def __call__(self, *, id: str, model: str, string: str = '',
                 inherit: str | None = None, priority: int | None = None,
                 **kwargs):
        """Decorator for standalone form views."""
        def decorator(fn):
            entry = {
                'type': 'form', 'fn': fn, 'id': id, 'model': model,
                'string': string, 'inherit': inherit, 'priority': priority,
                **kwargs,
            }
            _registry.views.append(entry)
            fn._odoo_view = entry
            return fn
        return decorator

    def extend(self, *, id: str, inherit: str, model: str,
               priority: int | None = None, **kwargs):
        """Decorator for inherited form views.

        ``model`` is **required** — Odoo needs it to validate
        the view's fields against the ORM model.

        Example::

            @view.form.extend(
                id='sale_order_form_custom',
                inherit='sale.view_order_form',
                model='sale.order',
            )
            def extend_sale_order(v):
                with v.inside('header'):
                    v.button('action_do', 'Do Something')
        """
        def decorator(fn):
            entry = {
                'type': 'form', 'subtype': 'extend', 'fn': fn,
                'id': id, 'model': model, 'inherit': inherit,
                'priority': priority, **kwargs,
            }
            _registry.views.append(entry)
            fn._odoo_view = entry
            return fn
        return decorator


class _ViewRegistry:
    """Central registry for ``@view.list`` and ``@view.form`` decorators."""

    def __init__(self):
        self.list = _ListDecorator()
        self.form = _FormDecorator()


view = _ViewRegistry()
