"""Extending the sale order form — the README side-by-side example."""
from odoo_views_dsl import view


@view.form.extend(
    id='sale_order_form_warehouse',
    inherit='sale.view_order_form',
)
def extend_sale_order(v):
    # Header button
    with v.inside('header'):
        v.button('action_send_to_warehouse', 'Send to Warehouse',
                 style='primary',
                 visible="has_products and not order_id "
                         "and state in ('sale', 'done')",
                 confirm='Submit this order for fulfillment?')

    # Smart button
    with v.inside('div[@name="button_box"]'):
        v.stat_button('action_view_bill', 'Vendor Bill',
                      icon='fa-money', visible='vendor_bill_id')

    # Hidden fields after partner_id
    v.after('partner_id',
            v.hidden('has_products', 'order_id', 'vendor_bill_id'))

    # New tab
    with v.tab('Warehouse', visible='order_id'):
        with v.group('Order'):
            v.field('order_name')
            v.field('shipping_method')
        with v.group('Tracking', visible='tracking_info'):
            v.field('tracking_info', widget='text', nolabel=True)
