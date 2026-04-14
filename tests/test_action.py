"""Tests for @action.window → XML compilation."""
import xml.etree.ElementTree as ET

from odoo_views_dsl import action
from odoo_views_dsl.compiler import compile_registry


def _parse(xml_str: str) -> ET.Element:
    if xml_str.startswith('<?xml'):
        xml_str = xml_str.split('?>', 1)[1].strip()
    return ET.fromstring(xml_str)


class TestAction:

    def test_basic_action(self):
        @action.window(
            id='action_partners',
            model='res.partner',
            string='Partners',
        )
        def partners(a):
            pass

        xml = compile_registry()
        root = _parse(xml)

        rec = root.find("record[@id='action_partners']")
        assert rec.get('model') == 'ir.actions.act_window'
        assert rec.find("field[@name='name']").text == 'Partners'
        assert rec.find("field[@name='res_model']").text == 'res.partner'
        assert rec.find("field[@name='view_mode']").text == 'list,form'

    def test_action_with_domain(self):
        @action.window(
            id='action_active',
            model='res.partner',
            string='Active',
            domain=[('active', '=', True)],
        )
        def active_partners(a):
            pass

        xml = compile_registry()
        root = _parse(xml)

        domain = root.find(".//field[@name='domain']")
        assert domain.text == "[('active', '=', True)]"

    def test_action_with_custom_views(self):
        @action.window(
            id='action_custom',
            model='res.partner',
            string='Custom',
        )
        def custom(a):
            a.view_list('partner_list')
            a.view_form('partner_form')

        xml = compile_registry()
        root = _parse(xml)

        vm = root.find(".//field[@name='view_mode']")
        assert vm.text == 'list,form'

    def test_action_with_search_filters(self):
        @action.window(
            id='action_filtered',
            model='sale.order',
            string='Orders',
            default_filters={'confirmed': 1},
        )
        def orders(a):
            a.search_filter('confirmed', 'Confirmed',
                            domain=[('state', '=', 'sale')])

        xml = compile_registry()
        root = _parse(xml)

        # Should have search view record
        search_rec = root.find("record[@id='action_filtered_search']")
        assert search_rec is not None

        filt = search_rec.find('.//filter')
        assert filt.get('name') == 'confirmed'
        assert filt.get('string') == 'Confirmed'

        # Action should reference search view
        action_rec = root.find("record[@id='action_filtered']")
        ref = action_rec.find("field[@name='search_view_id']")
        assert ref.get('ref') == 'action_filtered_search'

        # Context should have search_default_confirmed
        ctx = action_rec.find("field[@name='context']")
        assert 'search_default_confirmed' in ctx.text

    def test_action_view_mode_from_builder(self):
        """Builder-declared views should set view_mode on the action."""
        @action.window(
            id='action_form_first',
            model='res.partner',
            string='Form First',
        )
        def form_first(a):
            a.view_form('partner_form')
            a.view_list('partner_list')

        xml = compile_registry()
        root = _parse(xml)

        vm = root.find(".//field[@name='view_mode']")
        assert vm.text == 'form,list'

    def test_search_fields_and_separator(self):
        """search_field() and search_separator() populate the search view."""
        @action.window(
            id='action_search_fields',
            model='sale.order',
            string='Orders',
        )
        def orders(a):
            a.search_field('name')
            a.search_field('partner_id')
            a.search_separator()
            a.search_filter('submitted', 'Submitted',
                            domain=[('order_id', '!=', False)])

        xml = compile_registry()
        root = _parse(xml)

        search_rec = root.find("record[@id='action_search_fields_search']")
        assert search_rec is not None

        search_el = search_rec.find('.//search')
        children = list(search_el)
        assert children[0].tag == 'field'
        assert children[0].get('name') == 'name'
        assert children[1].tag == 'field'
        assert children[1].get('name') == 'partner_id'
        assert children[2].tag == 'separator'
        assert children[3].tag == 'filter'
        assert children[3].get('name') == 'submitted'

    def test_view_id_ref(self):
        """view_id generates <field name='view_id' ref='...'/>."""
        @action.window(
            id='action_with_view',
            model='product.template',
            string='Products',
            view_id='custom_product_list',
        )
        def products(a):
            pass

        xml = compile_registry()
        root = _parse(xml)

        ref = root.find(".//field[@name='view_id']")
        assert ref is not None
        assert ref.get('ref') == 'custom_product_list'

    def test_help_text(self):
        """help generates smiling-face empty-state HTML."""
        @action.window(
            id='action_with_help',
            model='product.template',
            string='Products',
            help='No products found.',
        )
        def products(a):
            pass

        xml = compile_registry()
        root = _parse(xml)

        help_field = root.find(".//field[@name='help']")
        assert help_field is not None
        assert help_field.get('type') == 'html'

        p = help_field.find('p')
        assert 'o_view_nocontent_smiling_face' in p.get('class')
        assert p.text == 'No products found.'

    def test_target(self):
        """target generates <field name='target'>inline</field>."""
        @action.window(
            id='action_settings',
            model='res.config.settings',
            string='Settings',
            view_mode='form',
            target='inline',
            context={'module': 'my_module'},
        )
        def settings(a):
            pass

        xml = compile_registry()
        root = _parse(xml)

        target = root.find(".//field[@name='target']")
        assert target.text == 'inline'

        ctx = root.find(".//field[@name='context']")
        assert "'module': 'my_module'" in ctx.text

    def test_act_window_view_records(self):
        """view_list()/view_form() generate ir.actions.act_window.view records."""
        @action.window(
            id='action_bound',
            model='sale.order',
            string='Orders',
        )
        def orders(a):
            a.view_list('order_list_custom')
            a.view_form('order_form_custom')

        xml = compile_registry()
        root = _parse(xml)

        # List view binding
        list_rec = root.find("record[@id='action_bound_list']")
        assert list_rec is not None
        assert list_rec.get('model') == 'ir.actions.act_window.view'
        assert list_rec.find("field[@name='sequence']").text == '1'
        assert list_rec.find("field[@name='view_mode']").text == 'list'
        assert list_rec.find("field[@name='view_id']").get('ref') == 'order_list_custom'
        assert list_rec.find("field[@name='act_window_id']").get('ref') == 'action_bound'

        # Form view binding
        form_rec = root.find("record[@id='action_bound_form']")
        assert form_rec is not None
        assert form_rec.find("field[@name='sequence']").text == '2'

    def test_full_avexpress_action(self):
        """Full real-world action: sale orders with search fields, filters, view binding."""
        @action.window(
            id='action_avexpress_sale_orders',
            model='sale.order',
            string='AV Express Orders',
            domain=[('has_avexpress_products', '=', True)],
            default_filters={'submitted': 1},
        )
        def avx_orders(a):
            a.view_list('sale_order_tree_avexpress')
            a.search_field('name')
            a.search_field('partner_id')
            a.search_field('avexpress_order_name')
            a.search_separator()
            a.search_filter('not_submitted', 'Not Yet Submitted',
                            domain=[('avexpress_order_id', '=', False)])
            a.search_filter('submitted', 'Submitted to AVX',
                            domain=[('avexpress_order_id', '!=', False)])
            a.search_filter('has_tracking', 'Has Tracking',
                            domain=[('avexpress_tracking_info', '!=', False)])

        xml = compile_registry()
        root = _parse(xml)

        # Search view has 3 fields + separator + 3 filters
        search_el = root.find('.//search')
        children = list(search_el)
        assert len(children) == 7  # 3 fields + 1 sep + 3 filters

        # Action has view binding
        list_rec = root.find("record[@id='action_avexpress_sale_orders_list']")
        assert list_rec is not None
        assert list_rec.find("field[@name='view_id']").get('ref') == 'sale_order_tree_avexpress'

