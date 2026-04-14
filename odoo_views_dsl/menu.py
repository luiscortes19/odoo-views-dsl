"""Menu helpers: ``menu.root``, ``menu.item``."""
from __future__ import annotations

from . import _registry


class _MenuRegistry:
    """Collects menu definitions for later compilation to XML."""

    def root(self, name: str, *, icon: str | None = None, sequence: int = 90):
        """Define the top-level application menu.

        Example::

            menu.root('Warehouse', icon='wh_module,static/description/icon.png',
                       sequence=90)
        """
        _registry.menus.append({
            'type': 'root',
            'name': name,
            'icon': icon,
            'sequence': sequence,
        })

    def item(self, path: str, *, action: str | None = None,
             sequence: int | None = None, groups: str | None = None):
        """Define a menu item via a slash-separated path.

        Intermediate parent menus are auto-created.  IDs are auto-generated
        from the path segments.

        Example::

            menu.item('Warehouse / Catalog / Products', action='product_list')
        """
        _registry.menus.append({
            'type': 'item',
            'path': path,
            'action': action,
            'sequence': sequence,
            'groups': groups,
        })


menu = _MenuRegistry()
