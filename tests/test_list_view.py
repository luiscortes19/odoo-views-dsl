"""Tests for @view.list → XML compilation."""
import xml.etree.ElementTree as ET

from odoo_views_dsl import view
from odoo_views_dsl.compiler import compile_registry


def _parse(xml_str: str) -> ET.Element:
    """Parse XML string, stripping declaration if present."""
    if xml_str.startswith('<?xml'):
        xml_str = xml_str.split('?>', 1)[1].strip()
    return ET.fromstring(xml_str)


class TestBasicListView:

    def test_minimal_list(self):
        @view.list(id='test_list', model='res.partner', string='Partners')
        def partner_list(v):
            v.column('name', 'Name')
            v.column('email', 'Email')

        xml = compile_registry()
        root = _parse(xml)

        # Should have one record
        records = root.findall('record')
        assert len(records) == 1

        rec = records[0]
        assert rec.get('id') == 'test_list'
        assert rec.get('model') == 'ir.ui.view'

        # Check name field
        name_field = rec.find("field[@name='name']")
        assert name_field.text == 'test.list'

        # Check model field
        model_field = rec.find("field[@name='model']")
        assert model_field.text == 'res.partner'

        # Check arch
        arch = rec.find("field[@name='arch']")
        list_el = arch.find('list')
        assert list_el.get('string') == 'Partners'

        fields = list_el.findall('field')
        assert len(fields) == 2
        assert fields[0].get('name') == 'name'
        assert fields[0].get('string') == 'Name'
        assert fields[1].get('name') == 'email'
        assert fields[1].get('string') == 'Email'

    def test_list_with_decorations(self):
        @view.list(
            id='decorated_list',
            model='product.template',
            string='Products',
            decorations={
                'success': "state == 'done'",
                'danger': "state == 'error'",
            },
        )
        def product_list(v):
            v.column('name', 'Name')

        xml = compile_registry()
        root = _parse(xml)

        arch = root.find(".//field[@name='arch']")
        list_el = arch.find('list')
        assert list_el.get('decoration-success') == "state == 'done'"
        assert list_el.get('decoration-danger') == "state == 'error'"

    def test_header_button(self):
        @view.list(id='btn_list', model='res.partner', string='Test')
        def test_list(v):
            v.header_button('action_do', 'Do It', style='primary')
            v.column('name')

        xml = compile_registry()
        root = _parse(xml)

        list_el = root.find('.//list')
        header = list_el.find('header')
        assert header is not None

        btn = header.find('button')
        assert btn.get('name') == 'action_do'
        assert btn.get('string') == 'Do It'
        assert btn.get('class') == 'btn-primary'
        assert btn.get('type') == 'object'

    def test_badge_column(self):
        @view.list(id='badge_list', model='res.partner', string='Test')
        def test_list(v):
            v.badge('state', 'Status', success='done', danger='error')

        xml = compile_registry()
        root = _parse(xml)

        field = root.find(".//list/field[@name='state']")
        assert field.get('widget') == 'badge'
        assert field.get('string') == 'Status'
        assert field.get('decoration-success') == "state == 'done'"
        assert field.get('decoration-danger') == "state == 'error'"

    def test_column_with_decoration(self):
        @view.list(id='dec_list', model='res.partner', string='Test')
        def test_list(v):
            v.column('qty', 'Quantity', decoration_danger='qty < 0')

        xml = compile_registry()
        root = _parse(xml)

        field = root.find(".//list/field[@name='qty']")
        assert field.get('decoration-danger') == 'qty < 0'

    def test_column_with_widget(self):
        @view.list(id='widget_list', model='res.partner', string='Test')
        def test_list(v):
            v.column('amount', 'Amount', widget='monetary')

        xml = compile_registry()
        root = _parse(xml)

        field = root.find(".//list/field[@name='amount']")
        assert field.get('widget') == 'monetary'

    def test_xml_escaping(self):
        """Verify that < in expressions is properly escaped in XML output."""
        @view.list(id='esc_list', model='res.partner', string='Test')
        def test_list(v):
            v.column('qty', 'Qty', decoration_danger='qty < 0')

        xml = compile_registry()
        # The raw XML string should contain &lt; (escaped <)
        assert 'qty &lt; 0' in xml
