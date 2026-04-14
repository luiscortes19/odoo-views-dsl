"""Tests for menu.root / menu.item → XML compilation."""
import xml.etree.ElementTree as ET

from odoo_views_dsl import menu
from odoo_views_dsl.compiler import compile_registry


def _parse(xml_str: str) -> ET.Element:
    if xml_str.startswith('<?xml'):
        xml_str = xml_str.split('?>', 1)[1].strip()
    return ET.fromstring(xml_str)


class TestMenu:

    def test_root_menu(self):
        menu.root('Warehouse', icon='wh,static/icon.png', sequence=90)

        xml = compile_registry()
        root = _parse(xml)

        items = root.findall('menuitem')
        assert len(items) == 1
        assert items[0].get('id') == 'menu_warehouse_root'
        assert items[0].get('name') == 'Warehouse'
        assert items[0].get('web_icon') == 'wh,static/icon.png'
        assert items[0].get('sequence') == '90'

    def test_path_based_items(self):
        menu.root('App', sequence=10)
        menu.item('App / Catalog / Products', action='product_list')
        menu.item('App / Catalog / Categories', action='category_list')
        menu.item('App / Config / Settings', action='app_settings')

        xml = compile_registry()
        root = _parse(xml)

        items = root.findall('menuitem')
        ids = [it.get('id') for it in items]

        # All expected menus present
        assert 'menu_app_root' in ids
        assert 'menu_app_catalog' in ids
        assert 'menu_app_catalog_products' in ids
        assert 'menu_app_catalog_categories' in ids
        assert 'menu_app_config' in ids
        assert 'menu_app_config_settings' in ids

        # Check parent references
        cat = next(i for i in items if i.get('id') == 'menu_app_catalog')
        assert cat.get('parent') == 'menu_app_root'

        prod = next(i for i in items if i.get('id') == 'menu_app_catalog_products')
        assert prod.get('parent') == 'menu_app_catalog'
        assert prod.get('action') == 'product_list'

    def test_auto_creates_root(self):
        """Root is auto-created if menu.root() wasn't called."""
        menu.item('MyApp / Settings', action='my_settings')

        xml = compile_registry()
        root = _parse(xml)

        items = root.findall('menuitem')
        ids = [it.get('id') for it in items]
        assert 'menu_myapp_root' in ids
        assert 'menu_myapp_settings' in ids

    def test_explicit_sequence(self):
        menu.root('App', sequence=10)
        menu.item('App / First', action='first', sequence=5)

        xml = compile_registry()
        root = _parse(xml)

        leaf = root.find(".//menuitem[@id='menu_app_first']")
        assert leaf.get('sequence') == '5'

    def test_shared_intermediate_parents(self):
        """Two items sharing a parent shouldn't duplicate it."""
        menu.root('Sales', sequence=10)
        menu.item('Sales / Orders / Quotations', action='quotation_list')
        menu.item('Sales / Orders / Confirmed', action='confirmed_list')

        xml = compile_registry()
        root = _parse(xml)

        items = root.findall('menuitem')
        ids = [it.get('id') for it in items]

        # 'menu_sales_orders' should appear exactly once
        assert ids.count('menu_sales_orders') == 1

        # Both leaf items should exist
        assert 'menu_sales_orders_quotations' in ids
        assert 'menu_sales_orders_confirmed' in ids
