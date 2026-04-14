"""Action decorators: ``@action.window``."""
from __future__ import annotations

from . import _registry


class _ActionRegistry:
    """Collects action definitions for later compilation to XML."""

    def window(self, *, id: str, model: str, string: str = '',
               domain=None, default_filters: dict | None = None,
               view_mode: str = 'list,form', context: dict | None = None,
               limit: int | None = None, view_id: str | None = None,
               help: str | None = None, target: str | None = None,
               **kwargs):
        """Decorator for window actions (``act_window``).

        Parameters
        ----------
        view_id : str, optional
            XML ID of the default view (generates ``<field name="view_id" ref="..."/>``).
        help : str, optional
            Empty-state help text (wrapped in smiling-face pattern).
        target : str, optional
            Window target: ``'current'``, ``'new'``, ``'inline'``, ``'fullscreen'``.

        Example::

            @action.window(
                id='warehouse_orders',
                model='sale.order',
                string='Warehouse Orders',
                domain=[('has_warehouse', '=', True)],
                default_filters={'submitted': 1},
            )
            def warehouse_orders(a):
                a.view_list('warehouse_order_list')
                a.search_filter('submitted', 'Submitted',
                                domain=[('order_id', '!=', False)])
        """
        def decorator(fn):
            entry = {
                'type': 'window', 'fn': fn, 'id': id, 'model': model,
                'string': string, 'domain': domain,
                'default_filters': default_filters or {},
                'view_mode': view_mode, 'context': context,
                'limit': limit, 'view_id': view_id,
                'help': help, 'target': target, **kwargs,
            }
            _registry.actions.append(entry)
            fn._odoo_action = entry
            return fn
        return decorator


action = _ActionRegistry()
