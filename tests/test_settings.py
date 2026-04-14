"""Tests for @settings.page → res.config.settings view generation."""
import xml.etree.ElementTree as ET

from odoo_views_dsl import settings
from odoo_views_dsl.compiler import compile_registry


def _parse(xml_str: str) -> ET.Element:
    if xml_str.startswith('<?xml'):
        xml_str = xml_str.split('?>', 1)[1].strip()
    return ET.fromstring(xml_str)


class TestSettingsPage:

    def test_basic_settings_structure(self):
        """Settings page generates inherited view with <app>/<block>/<setting>."""
        @settings.page(
            id='config_test',
            module='test_module',
            string='Test App',
        )
        def test_settings(s):
            with s.block('General'):
                with s.setting('API Key', help='Enter your key.'):
                    s.field('api_key')

        xml = compile_registry()
        root = _parse(xml)

        rec = root.find('record')
        assert rec.get('id') == 'config_test'
        assert rec.get('model') == 'ir.ui.view'

        # Model is res.config.settings
        model = rec.find("field[@name='model']")
        assert model.text == 'res.config.settings'

        # Inherits base settings form
        inherit = rec.find("field[@name='inherit_id']")
        assert inherit.get('ref') == 'base.res_config_settings_view_form'

        # Arch has xpath targeting //form
        arch = rec.find("field[@name='arch']")
        xpath = arch.find('xpath')
        assert xpath.get('expr') == '//form'
        assert xpath.get('position') == 'inside'

        # App element
        app = xpath.find('app')
        assert app.get('data-string') == 'Test App'
        assert app.get('string') == 'Test App'
        assert app.get('name') == 'test_module'

        # Block → Setting → content-group → row → label + field
        block = app.find('block')
        assert block.get('title') == 'General'

        setting = block.find('setting')
        assert setting.get('string') == 'API Key'
        assert setting.get('help') == 'Enter your key.'

        cg = setting.find("div[@class='content-group']")
        assert cg is not None

        row = cg.find('div')
        assert 'row' in row.get('class')
        assert 'mt16' in row.get('class')

        label = row.find('label')
        assert label.get('for') == 'api_key'
        assert 'col-lg-3' in label.get('class')

        field = row.find('field')
        assert field.get('name') == 'api_key'
        assert 'col-lg-9' in field.get('class')

    def test_multiple_fields_in_setting(self):
        """Multiple fields get mt16 for first, mt8 for subsequent."""
        @settings.page(
            id='config_multi',
            module='test_mod',
            string='Test',
        )
        def multi_settings(s):
            with s.block('Connection'):
                with s.setting('API Endpoint', help='Config your API.'):
                    s.field('api_url', readonly=True)
                    s.field('api_key', password=True)

        xml = compile_registry()
        root = _parse(xml)

        cg = root.find('.//div[@class="content-group"]')
        rows = cg.findall('div')
        assert len(rows) == 2

        # First row: mt16
        assert 'mt16' in rows[0].get('class')
        assert rows[0].find('field').get('readonly') == '1'

        # Second row: mt8
        assert 'mt8' in rows[1].get('class')
        assert rows[1].find('field').get('password') == 'True'

    def test_field_with_widget(self):
        """Widget kwarg is passed through."""
        @settings.page(
            id='config_widget',
            module='test_mod',
            string='Test',
        )
        def widget_settings(s):
            with s.block('Env'):
                with s.setting('Environment'):
                    s.field('environment', widget='radio')

        xml = compile_registry()
        root = _parse(xml)

        field = root.find('.//field[@name="environment"]')
        assert field.get('widget') == 'radio'

    def test_field_with_placeholder(self):
        """Placeholder kwarg passes through."""
        @settings.page(
            id='config_placeholder',
            module='test_mod',
            string='Test',
        )
        def placeholder_settings(s):
            with s.block('Account'):
                with s.setting('Company ID'):
                    s.field('company_id', placeholder='e.g. 4897603733')

        xml = compile_registry()
        root = _parse(xml)

        field = root.find('.//field[@name="company_id"]')
        assert field.get('placeholder') == 'e.g. 4897603733'

    def test_checkbox(self):
        """checkbox() generates field + label inline."""
        @settings.page(
            id='config_checkbox',
            module='test_mod',
            string='Test',
        )
        def checkbox_settings(s):
            with s.block('Sync'):
                with s.setting('Auto-Sync', help='Automatically poll API.'):
                    s.checkbox('auto_sync')

        xml = compile_registry()
        root = _parse(xml)

        setting = root.find('.//setting')
        # checkbox div is a direct child of setting, not inside content-group
        div = setting.find("div[@class='mt8']")
        assert div is not None

        children = list(div)
        assert children[0].tag == 'field'
        assert children[0].get('name') == 'auto_sync'
        assert children[1].tag == 'label'
        assert children[1].get('for') == 'auto_sync'

    def test_conditional_field(self):
        """visible= wraps field in invisible div."""
        @settings.page(
            id='config_visible',
            module='test_mod',
            string='Test',
        )
        def visible_settings(s):
            with s.block('Sync'):
                with s.setting('Auto-Sync'):
                    s.checkbox('auto_sync')
                    s.field('sync_interval', visible='auto_sync',
                            suffix='hours between syncs')

        xml = compile_registry()
        root = _parse(xml)

        setting = root.find('.//setting')

        # Visibility wrapper
        wrapper = setting.find("div[@invisible='not auto_sync']")
        assert wrapper is not None

        # Row inside wrapper
        row = wrapper.find('div')
        assert 'row' in row.get('class')

        # Field is col-lg-2 (narrowed for suffix)
        field = row.find('field')
        assert field.get('name') == 'sync_interval'
        assert 'col-lg-2' in field.get('class')

        # Suffix span
        span = row.find('span')
        assert span.text == 'hours between syncs'
        assert 'col-lg-7' in span.get('class')

    def test_button_after_fields(self):
        """Button in a setting with prior fields goes in content-group row."""
        @settings.page(
            id='config_btn_cg',
            module='test_mod',
            string='Test',
        )
        def btn_settings(s):
            with s.block('API'):
                with s.setting('API Config'):
                    s.field('api_url', readonly=True)
                    s.button('action_test', 'Test Connection',
                             style='primary', icon='fa-plug')

        xml = compile_registry()
        root = _parse(xml)

        cg = root.find('.//div[@class="content-group"]')
        rows = cg.findall('div')
        assert len(rows) == 2

        # Second row is the button row
        btn_row = rows[1]
        assert 'row' in btn_row.get('class')

        # Empty label column + button cell
        cols = list(btn_row)
        assert cols[0].tag == 'div'
        assert 'col-lg-3' in cols[0].get('class')
        btn_cell = cols[1]
        assert 'col-lg-9' in btn_cell.get('class')

        btn = btn_cell.find('button')
        assert btn.get('name') == 'action_test'
        assert btn.get('class') == 'btn-primary'
        assert btn.get('icon') == 'fa-plug'

    def test_standalone_button(self):
        """Button without prior fields goes in a simple div."""
        @settings.page(
            id='config_btn_standalone',
            module='test_mod',
            string='Test',
        )
        def standalone_btn(s):
            with s.block('Sync'):
                with s.setting('Manual Sync', help='Trigger now.'):
                    s.button('action_sync', 'Sync Now',
                             style='secondary', icon='fa-refresh')

        xml = compile_registry()
        root = _parse(xml)

        setting = root.find('.//setting')
        div = setting.find("div[@class='mt8']")
        assert div is not None

        btn = div.find('button')
        assert btn.get('name') == 'action_sync'
        assert btn.get('class') == 'btn-secondary'

    def test_multiple_blocks(self):
        """Multiple blocks are siblings inside <app>."""
        @settings.page(
            id='config_multi_blocks',
            module='test_mod',
            string='Test',
        )
        def multi_blocks(s):
            with s.block('Connection'):
                with s.setting('URL'):
                    s.field('url')
            with s.block('Warehouse'):
                with s.setting('Location'):
                    s.field('location_id')

        xml = compile_registry()
        root = _parse(xml)

        app = root.find('.//app')
        blocks = app.findall('block')
        assert len(blocks) == 2
        assert blocks[0].get('title') == 'Connection'
        assert blocks[1].get('title') == 'Warehouse'

    def test_full_avexpress_settings(self):
        """Full real-world settings page matching the avexpress_integration module."""
        @settings.page(
            id='res_config_settings_view_form_avexpress',
            module='avexpress_integration',
            string='AV Express',
        )
        def avexpress_settings(s):
            with s.block('Environment'):
                with s.setting('API Environment',
                               help='Switch between Sandbox (testing) and '
                                    'Production (live orders).'):
                    s.field('avexpress_environment', widget='radio')

            with s.block('API Connection'):
                with s.setting('API Endpoint',
                               help='Credentials auto-fill when you switch environment.'):
                    s.field('avexpress_api_url', readonly=True)
                    s.field('avexpress_api_key', password=True)
                    s.button('action_avexpress_test_connection',
                             'Test Connection', style='primary', icon='fa-plug')

            with s.block('Identity & Pricing'):
                with s.setting('AV Express Account',
                               help='HH Pockets identity on AV Express and '
                                    'pricing configuration.'):
                    s.field('avexpress_company_id',
                            placeholder='e.g. 4897603733')
                    s.field('avexpress_customer_id',
                            placeholder='optional (Nick recommends Company ID)')
                    s.field('avexpress_vendor_partner_id')
                    s.field('avexpress_commission_pricelist_id')

            with s.block('Warehouse'):
                with s.setting('AV Express Location',
                               help='The internal stock location representing '
                                    'inventory at AV Express\'s US warehouse.'):
                    s.field('avexpress_warehouse_location_id')

            with s.block('Inventory Sync'):
                with s.setting('Auto-Sync',
                               help='Automatically poll AV Express API for '
                                    'inventory changes.'):
                    s.checkbox('avexpress_auto_sync_inventory')
                    s.field('avexpress_sync_interval_hours',
                            visible='avexpress_auto_sync_inventory',
                            suffix='hours between syncs')
                with s.setting('Manual Sync',
                               help='Trigger an inventory sync right now.'):
                    s.button('action_avexpress_sync_inventory',
                             'Sync Inventory Now',
                             style='secondary', icon='fa-refresh')

        xml = compile_registry()
        root = _parse(xml)

        # Structure checks
        app = root.find('.//app')
        assert app.get('name') == 'avexpress_integration'

        blocks = app.findall('block')
        assert len(blocks) == 5
        assert [b.get('title') for b in blocks] == [
            'Environment', 'API Connection', 'Identity & Pricing',
            'Warehouse', 'Inventory Sync',
        ]

        # API Connection: 2 fields + 1 button in content-group
        api_cg = blocks[1].find('.//div[@class="content-group"]')
        assert len(api_cg.findall('div')) == 3

        # Identity: 4 fields
        identity_cg = blocks[2].find('.//div[@class="content-group"]')
        assert len(identity_cg.findall('div')) == 4

        # Auto-Sync: checkbox + conditional field
        sync_settings = blocks[4].findall('setting')
        auto_sync = sync_settings[0]
        checkbox_div = auto_sync.find("div[@class='mt8']")
        assert checkbox_div is not None  # checkbox

        invisible_div = auto_sync.find("div[@invisible='not avexpress_auto_sync_inventory']")
        assert invisible_div is not None  # conditional field

        # Manual Sync: standalone button
        manual_sync = sync_settings[1]
        btn_div = manual_sync.find("div[@class='mt8']")
        assert btn_div.find('button').get('name') == 'action_avexpress_sync_inventory'
