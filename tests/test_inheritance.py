"""Tests for view inheritance — @view.form.extend, @view.list.extend, XPath generation."""
import xml.etree.ElementTree as ET

from odoo_views_dsl import view
from odoo_views_dsl.compiler import compile_registry


def _parse(xml_str: str) -> ET.Element:
    if xml_str.startswith('<?xml'):
        xml_str = xml_str.split('?>', 1)[1].strip()
    return ET.fromstring(xml_str)


# ─── Form Inheritance ────────────────────────────────────────────────

class TestFormExtend:

    def test_inside_header(self):
        """with v.inside('header') → <xpath expr='//header' position='inside'>"""
        @view.form.extend(
            id='sale_form_ext',
            inherit='sale.view_order_form',
            model='sale.order',
        )
        def extend_sale(v):
            with v.inside('header'):
                v.button('action_send', 'Send to Warehouse', style='primary')

        xml = compile_registry()
        root = _parse(xml)

        rec = root.find('record')
        assert rec.get('id') == 'sale_form_ext'

        # inherit_id ref
        inherit = rec.find("field[@name='inherit_id']")
        assert inherit.get('ref') == 'sale.view_order_form'

        # No <form> wrapper — arch contains xpath directly
        arch = rec.find("field[@name='arch']")
        assert arch.find('form') is None

        xpath = arch.find('xpath')
        assert xpath.get('expr') == '//header'
        assert xpath.get('position') == 'inside'

        btn = xpath.find('button')
        assert btn.get('name') == 'action_send'
        assert btn.get('class') == 'btn-primary'

    def test_after_field(self):
        """v.after('partner_id', ...) → <xpath position='after'>"""
        @view.form.extend(
            id='order_form_ext',
            inherit='sale.view_order_form',
            model='sale.order',
        )
        def extend_order(v):
            v.after('partner_id',
                    v.hidden('custom_field1', 'custom_field2'))

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == "//field[@name='partner_id']"
        assert xpath.get('position') == 'after'

        fields = xpath.findall('field')
        assert len(fields) == 2
        assert fields[0].get('name') == 'custom_field1'
        assert fields[0].get('invisible') == '1'

    def test_before_field(self):
        """v.before() → position='before'."""
        @view.form.extend(
            id='before_ext',
            inherit='sale.view_order_form',
            model='sale.order',
        )
        def extend_before(v):
            v.before('partner_id',
                     v.make_field('priority', 'Priority'))

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == "//field[@name='partner_id']"
        assert xpath.get('position') == 'before'

        field = xpath.find('field')
        assert field.get('name') == 'priority'
        assert field.get('string') == 'Priority'

    def test_tab_in_extend_mode(self):
        """v.tab() in extend mode → xpath targeting //notebook."""
        @view.form.extend(
            id='tab_ext',
            inherit='sale.view_order_form',
            model='sale.order',
        )
        def extend_with_tab(v):
            with v.tab('Warehouse', visible='order_id'):
                with v.group('Order'):
                    v.field('order_name')
                    v.field('shipping_method')

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == '//notebook'
        assert xpath.get('position') == 'inside'

        page = xpath.find('page')
        assert page.get('string') == 'Warehouse'
        assert page.get('invisible') == 'not (order_id)'

        group = page.find('group')
        assert group.get('string') == 'Order'
        assert len(group.findall('field')) == 2

    def test_header_auto_delegates_in_extend(self):
        """v.header() in extend mode → v.inside('header') automatically."""
        @view.form.extend(
            id='hdr_ext',
            inherit='sale.view_order_form',
            model='sale.order',
        )
        def extend_header(v):
            with v.header():
                v.button('action_do', 'Do It')

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == '//header'
        assert xpath.get('position') == 'inside'

    def test_inside_button_box(self):
        """inside('div[@name=\"button_box\"]') → correct xpath expression."""
        @view.form.extend(
            id='bbox_ext',
            inherit='sale.view_order_form',
            model='sale.order',
        )
        def extend_bbox(v):
            with v.inside('div[@name="button_box"]'):
                v.stat_button('action_view_bill', 'Vendor Bill',
                              icon='fa-money', visible='bill_id')

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == '//div[@name="button_box"]'
        assert xpath.get('position') == 'inside'

        btn = xpath.find('button')
        assert btn.get('class') == 'oe_stat_button'

    def test_full_real_world_extend(self):
        """The complete sale order extension from the README side-by-side."""
        @view.form.extend(
            id='sale_order_form_warehouse',
            inherit='sale.view_order_form',
            model='sale.order',
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

        xml = compile_registry()
        root = _parse(xml)

        xpaths = root.findall('.//xpath')
        # header, button_box, after partner_id, notebook
        assert len(xpaths) == 4

        exprs = {x.get('expr'): x.get('position') for x in xpaths}
        assert exprs['//header'] == 'inside'
        assert exprs['//div[@name="button_box"]'] == 'inside'
        assert exprs["//field[@name='partner_id']"] == 'after'
        assert exprs['//notebook'] == 'inside'

        # Hidden fields after partner_id
        after_xpath = [x for x in xpaths if x.get('position') == 'after'][0]
        hidden = after_xpath.findall('field')
        assert len(hidden) == 3
        assert all(f.get('invisible') == '1' for f in hidden)

    def test_model_is_emitted(self):
        """Inherited views include <field name='model'> in the record."""
        @view.form.extend(
            id='model_ext',
            inherit='sale.view_order_form',
            model='sale.order',
        )
        def extend_with_model(v):
            v.after('partner_id',
                    v.make_field('custom', 'Custom'))

        xml = compile_registry()
        root = _parse(xml)

        rec = root.find('record')
        model_field = rec.find("field[@name='model']")
        assert model_field is not None
        assert model_field.text == 'sale.order'


# ─── List Inheritance ────────────────────────────────────────────────

class TestListExtend:

    def test_list_extend_after(self):
        """@view.list.extend with after() → xpath on field."""
        @view.list.extend(
            id='partner_list_ext',
            inherit='base.partner_list',
            model='res.partner',
        )
        def extend_list(v):
            v.after('name', v.make_field('custom', 'Custom'))

        xml = compile_registry()
        root = _parse(xml)

        rec = root.find('record')
        assert rec.get('id') == 'partner_list_ext'

        inherit_field = rec.find("field[@name='inherit_id']")
        assert inherit_field.get('ref') == 'base.partner_list'

        # No <list> wrapper
        arch = rec.find("field[@name='arch']")
        assert arch.find('list') is None

        xpath = arch.find('xpath')
        assert xpath.get('expr') == "//field[@name='name']"
        assert xpath.get('position') == 'after'

        field = xpath.find('field')
        assert field.get('name') == 'custom'
        assert field.get('string') == 'Custom'

    def test_list_extend_before(self):
        """before() → position='before'."""
        @view.list.extend(
            id='list_before_ext',
            inherit='base.partner_list',
            model='res.partner',
        )
        def extend_before(v):
            v.before('email', v.make_field('phone', 'Phone'))

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == "//field[@name='email']"
        assert xpath.get('position') == 'before'

    def test_list_extend_header_button(self):
        """header_button() in extend mode auto-wraps in xpath."""
        @view.list.extend(
            id='list_hdr_ext',
            inherit='base.partner_list',
            model='res.partner',
        )
        def extend_header(v):
            v.header_button('action_batch', 'Batch Update', style='primary')

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == '//header'
        assert xpath.get('position') == 'inside'

        btn = xpath.find('button')
        assert btn.get('name') == 'action_batch'

    def test_list_extend_model_emitted(self):
        """Inherited list views include model in the record."""
        @view.list.extend(
            id='model_list_ext',
            inherit='base.partner_list',
            model='res.partner',
        )
        def extend_with_model(v):
            v.after('email', v.make_field('phone', 'Phone'))

        xml = compile_registry()
        root = _parse(xml)

        rec = root.find('record')
        model_field = rec.find("field[@name='model']")
        assert model_field is not None
        assert model_field.text == 'res.partner'

    def test_list_extend_inside_context(self):
        """inside() context manager on list builder."""
        @view.list.extend(
            id='inside_list_ext',
            inherit='base.partner_list',
            model='res.partner',
        )
        def extend_inside(v):
            with v.inside('header'):
                v.column('batch_action')

        xml = compile_registry()
        root = _parse(xml)

        xpath = root.find('.//xpath')
        assert xpath.get('expr') == '//header'
        assert xpath.get('position') == 'inside'
