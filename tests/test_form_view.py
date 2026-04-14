"""Tests for @view.form → XML compilation."""
import xml.etree.ElementTree as ET

from odoo_views_dsl import view
from odoo_views_dsl.compiler import compile_registry


def _parse(xml_str: str) -> ET.Element:
    if xml_str.startswith('<?xml'):
        xml_str = xml_str.split('?>', 1)[1].strip()
    return ET.fromstring(xml_str)


class TestFormView:

    def test_basic_form_with_sheet(self):
        @view.form(id='test_form', model='res.partner', string='Partner')
        def partner_form(v):
            with v.sheet():
                with v.group('Info'):
                    v.field('name')
                    v.field('email')

        xml = compile_registry()
        root = _parse(xml)

        rec = root.find('record')
        assert rec.get('id') == 'test_form'

        form_el = root.find('.//form')
        assert form_el.get('string') == 'Partner'

        sheet = form_el.find('sheet')
        assert sheet is not None

        group = sheet.find('group')
        assert group.get('string') == 'Info'

        fields = group.findall('field')
        assert len(fields) == 2
        assert fields[0].get('name') == 'name'
        assert fields[1].get('name') == 'email'

    def test_tabs_share_notebook(self):
        """Consecutive tabs should share the same <notebook>."""
        @view.form(id='tab_form', model='res.partner', string='Partner')
        def partner_form(v):
            with v.sheet():
                with v.tab('General'):
                    v.field('name')
                with v.tab('Details'):
                    v.field('comment')

        xml = compile_registry()
        root = _parse(xml)

        notebooks = root.findall('.//notebook')
        assert len(notebooks) == 1

        pages = notebooks[0].findall('page')
        assert len(pages) == 2
        assert pages[0].get('string') == 'General'
        assert pages[1].get('string') == 'Details'

        # Fields inside pages
        assert pages[0].find("field[@name='name']") is not None
        assert pages[1].find("field[@name='comment']") is not None

    def test_visible_to_invisible(self):
        @view.form(id='vis_form', model='res.partner', string='Partner')
        def partner_form(v):
            with v.tab('Secret', visible='is_admin'):
                v.field('secret_key', visible="state == 'active'")

        xml = compile_registry()
        root = _parse(xml)

        page = root.find('.//page')
        assert page.get('invisible') == 'not (is_admin)'

        field = page.find('field')
        assert field.get('invisible') == "not (state == 'active')"

    def test_header_with_buttons(self):
        @view.form(id='hdr_form', model='res.partner', string='Partner')
        def partner_form(v):
            with v.header():
                v.button('action_confirm', 'Confirm', style='primary')
            with v.sheet():
                v.field('name')

        xml = compile_registry()
        root = _parse(xml)

        header = root.find('.//form/header')
        assert header is not None
        btn = header.find('button')
        assert btn.get('name') == 'action_confirm'
        assert btn.get('class') == 'btn-primary'

    def test_stat_button(self):
        @view.form(id='stat_form', model='res.partner', string='Partner')
        def partner_form(v):
            v.stat_button('action_view', 'Invoices',
                          icon='fa-money', visible='invoice_count')

        xml = compile_registry()
        root = _parse(xml)

        btn = root.find('.//button')
        assert btn.get('class') == 'oe_stat_button'
        assert btn.get('icon') == 'fa-money'
        assert btn.get('invisible') == 'not (invoice_count)'

        span = btn.find('span')
        assert span.text == 'Invoices'

    def test_nested_groups(self):
        @view.form(id='nest_form', model='res.partner', string='Partner')
        def partner_form(v):
            with v.sheet():
                with v.group():
                    with v.group('Left'):
                        v.field('name')
                    with v.group('Right'):
                        v.field('email')

        xml = compile_registry()
        root = _parse(xml)

        outer = root.find('.//sheet/group')
        assert outer is not None

        inner = outer.findall('group')
        assert len(inner) == 2
        assert inner[0].get('string') == 'Left'
        assert inner[1].get('string') == 'Right'

    def test_button_with_confirm(self):
        @view.form(id='confirm_form', model='res.partner', string='Partner')
        def partner_form(v):
            v.button('action_delete', 'Delete', style='danger',
                     confirm='Are you sure?')

        xml = compile_registry()
        root = _parse(xml)

        btn = root.find('.//button')
        assert btn.get('confirm') == 'Are you sure?'

    def test_field_nolabel(self):
        @view.form(id='nolabel_form', model='res.partner', string='Partner')
        def partner_form(v):
            v.field('description', nolabel=True)

        xml = compile_registry()
        root = _parse(xml)

        field = root.find('.//field[@name="description"]')
        assert field.get('nolabel') == '1'

    def test_badge_field(self):
        @view.form(id='badge_form', model='res.partner', string='Partner')
        def partner_form(v):
            v.badge('state', success='active', danger='archived')

        xml = compile_registry()
        root = _parse(xml)

        field = root.find(".//field[@name='state']")
        assert field.get('widget') == 'badge'
        assert field.get('decoration-success') == "state == 'active'"
        assert field.get('decoration-danger') == "state == 'archived'"

    def test_hidden_fields(self):
        @view.form(id='hidden_form', model='res.partner', string='Partner')
        def partner_form(v):
            nodes = v.hidden('is_admin', 'is_staff')
            # hidden() returns nodes for use with .after() — append directly
            for n in nodes:
                v._target.append(n)

        xml = compile_registry()
        root = _parse(xml)

        fields = root.findall(".//form/field")
        assert len(fields) == 2
        assert all(f.get('invisible') == '1' for f in fields)
