"""Warehouse module views — the README example, now real."""
from odoo_views_dsl import view, menu, action


# ── List View ────────────────────────────────────────────────────────

@view.list(
    id='warehouse_product_dashboard_list',
    model='product.template',
    string='Warehouse Products',
    decorations={
        'success': "readiness == 'ready'",
        'warning': "readiness == 'incomplete'",
        'danger': "readiness == 'no_price'",
    },
)
def warehouse_product_list(v):
    v.header_button('action_refresh_all', '⟳ Refresh All', style='primary')
    v.column('default_code', 'SKU')
    v.column('name', 'Product')
    v.badge('readiness', 'Status',
            success='ready', warning='incomplete', danger='no_price')
    v.column('reported_qty', 'Actual')
    v.column('expected_qty', 'Expected')
    v.column('qty_discrepancy', 'Discrepancy',
             decoration_danger='qty_discrepancy != 0')
    v.column('last_sync', 'Last Sync')


# ── Form View ────────────────────────────────────────────────────────

@view.form(
    id='warehouse_product_form',
    model='product.template',
    string='Warehouse Product',
)
def warehouse_product_form(v):
    with v.header():
        v.button('action_refresh', '🔄 Refresh from Warehouse', style='primary')
    with v.sheet():
        with v.group():
            with v.group('General'):
                v.field('default_code')
                v.field('name')
            with v.group('Status'):
                v.badge('readiness', success='ready', danger='incomplete')
                v.field('readiness_notes', visible="readiness != 'ready'")
        with v.tab('Inventory'):
            with v.group('Quantities'):
                v.field('reported_qty')
                v.field('expected_qty')
                v.field('qty_discrepancy',
                        decoration_danger='qty_discrepancy != 0')
        with v.tab('Sync'):
            v.field('last_sync')
            v.field('sync_log', nolabel=True, widget='text')


# ── Action ───────────────────────────────────────────────────────────

@action.window(
    id='action_warehouse_product_dashboard',
    model='product.template',
    string='Warehouse Products',
    domain=[('is_warehouse', '=', True)],
    default_filters={'ready': 1},
)
def warehouse_dashboard(a):
    a.view_list('warehouse_product_dashboard_list')
    a.view_form('warehouse_product_form')
    a.search_filter('ready', 'Ready',
                    domain=[('readiness', '=', 'ready')])
    a.search_filter('incomplete', 'Incomplete',
                    domain=[('readiness', '=', 'incomplete')])


# ── Menus ────────────────────────────────────────────────────────────

menu.root('Warehouse', icon='warehouse_module,static/description/icon.png',
          sequence=90)
menu.item('Warehouse / Catalog / Products',
          action='action_warehouse_product_dashboard')
menu.item('Warehouse / Operations / Sync Logs',
          action='action_warehouse_sync_log')
menu.item('Warehouse / Configuration / Settings',
          action='action_warehouse_config')
