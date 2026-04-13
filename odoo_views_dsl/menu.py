# Stub — implementation planned
"""Menu helpers: menu.root, menu.item"""


class _MenuRegistry:
    """Collects menu definitions for later compilation to XML."""

    def __init__(self):
        self._items = []

    def root(self, name, icon=None, sequence=90):
        """Define the top-level app menu."""
        self._items.append({
            'type': 'root',
            'name': name,
            'icon': icon,
            'sequence': sequence,
        })

    def item(self, path, action=None, sequence=None):
        """Define a menu item using a slash-separated path.

        Example:
            menu.item('Warehouse / Catalog / Products', action='product_list')
        """
        self._items.append({
            'type': 'item',
            'path': path,
            'action': action,
            'sequence': sequence,
        })


menu = _MenuRegistry()
