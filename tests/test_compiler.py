"""Integration tests for the compiler pipeline."""
from pathlib import Path

from odoo_views_dsl.compiler import compile_module


class TestCompileModule:

    def test_compile_single_file(self, tmp_path):
        dsl_file = tmp_path / 'views.py'
        dsl_file.write_text(
            'from odoo_views_dsl import view, menu\n'
            '\n'
            "@view.list(id='partner_list', model='res.partner', string='Partners')\n"
            'def partner_list(v):\n'
            "    v.column('name', 'Name')\n"
            "    v.column('email', 'Email')\n"
            '\n'
            "menu.root('Contacts', sequence=10)\n"
            "menu.item('Contacts / Partners', action='partner_list')\n",
            encoding='utf-8',
        )

        output_dir = tmp_path / 'output'
        result = compile_module(dsl_file, output_dir)

        assert '_generated_views.xml' in result

        xml_file = output_dir / '_generated_views.xml'
        assert xml_file.exists()

        content = xml_file.read_text(encoding='utf-8')
        assert 'partner_list' in content
        assert 'res.partner' in content
        assert 'menu_contacts_root' in content

    def test_compile_directory(self, tmp_path):
        pkg = tmp_path / 'my_module'
        pkg.mkdir()
        (pkg / '__init__.py').write_text('# module\n', encoding='utf-8')
        (pkg / 'views.py').write_text(
            'from odoo_views_dsl import view\n'
            '\n'
            "@view.list(id='item_list', model='my.item', string='Items')\n"
            'def item_list(v):\n'
            "    v.column('name')\n",
            encoding='utf-8',
        )

        result = compile_module(pkg)

        assert '_generated_views.xml' in result
        assert (pkg / 'views' / '_generated_views.xml').exists()

    def test_dry_run_no_files_written(self, tmp_path):
        dsl_file = tmp_path / 'views.py'
        dsl_file.write_text(
            'from odoo_views_dsl import view\n'
            '\n'
            "@view.list(id='dry_list', model='res.partner', string='Test')\n"
            'def test_list(v):\n'
            "    v.column('name')\n",
            encoding='utf-8',
        )

        result = compile_module(dsl_file, dry_run=True)

        assert '_generated_views.xml' in result
        # No file should be written
        assert not (tmp_path / 'views' / '_generated_views.xml').exists()

    def test_empty_source(self, tmp_path):
        dsl_file = tmp_path / 'empty.py'
        dsl_file.write_text('# Nothing here\n', encoding='utf-8')

        result = compile_module(dsl_file)
        assert result == {}

    def test_output_is_valid_xml(self, tmp_path):
        """The generated file should parse as valid XML."""
        import xml.etree.ElementTree as ET

        dsl_file = tmp_path / 'views.py'
        dsl_file.write_text(
            'from odoo_views_dsl import view\n'
            '\n'
            "@view.list(id='valid_list', model='res.partner', string='Test')\n"
            'def test_list(v):\n'
            "    v.column('qty', 'Qty', decoration_danger='qty < 0')\n",
            encoding='utf-8',
        )

        output_dir = tmp_path / 'output'
        result = compile_module(dsl_file, output_dir)

        xml_content = result['_generated_views.xml']
        # Should parse without errors (proves escaping is correct)
        root = ET.fromstring(
            xml_content.split('?>', 1)[1].strip()
            if xml_content.startswith('<?xml')
            else xml_content
        )
        assert root.tag == 'odoo'
