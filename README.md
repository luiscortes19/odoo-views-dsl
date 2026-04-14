# odoo-views-dsl

Write Odoo views, menus, and actions in Python. Compile to standard XML.
**Never touch `<record>`/`<field>` XML again.**

## Install

```bash
pip install -e .          # from the repo root
# or
pip install -e ".[dev]"   # includes pytest
```

## Usage

### 1. Write your views in Python

Create a `.py` file inside your Odoo module (e.g. `views_dsl/product_views.py`):

```python
from odoo_views_dsl import view, action, menu, settings

# ── Standalone list view ─────────────────────────────

@view.list(
    id='product_dashboard_list',
    model='product.template',
    string='My Products',
    decorations={'success': "status == 'ready'"},
)
def product_list(v):
    v.header_button('action_refresh', 'Refresh All', style='primary')
    v.column('default_code', 'Article #')
    v.column('name', 'Product')
    v.badge('status', 'Status', success='ready', danger='error')
    v.column('last_sync', 'Last Sync')

# ── Standalone form view ─────────────────────────────

@view.form(
    id='product_dashboard_form',
    model='product.template',
    string='Product',
)
def product_form(v):
    with v.header():
        v.button('action_refresh', 'Refresh', style='primary')
    with v.sheet():
        with v.group('General'):
            v.field('name')
            v.field('default_code')
        with v.tab('Inventory'):
            with v.group('Stock'):
                v.field('qty_available')

# ── Inherited view (XPath) ───────────────────────────

@view.form.extend(
    id='sale_order_form_custom',
    inherit='sale.view_order_form',
)
def extend_sale_order(v):
    with v.inside('header'):
        v.button('action_do', 'Do Thing', style='primary')

    with v.inside('div[@name="button_box"]'):
        v.stat_button('action_view_bill', 'Bill', icon='fa-money')

    v.after('partner_id',
            v.hidden('has_products', 'order_id'))

    with v.tab('Custom Tab', name='custom_tab', visible='order_id'):
        with v.group('Details'):
            v.field('custom_field')

# ── Actions ──────────────────────────────────────────

@action.window(
    id='action_product_dashboard',
    model='product.template',
    string='My Products',
    domain=[('is_active', '=', True)],
    view_id='product_dashboard_list',
    help='No products found.',
)
def product_action(a):
    a.view_list('product_dashboard_list')
    a.search_field('name')
    a.search_field('default_code')
    a.search_separator()
    a.search_filter('active', 'Active',
                    domain=[('active', '=', True)])

# ── Menus ────────────────────────────────────────────

menu.root('my_module_root', 'My Module', web_icon='my_module,static/description/icon.png')
menu.item('My Module / Products / Dashboard', action='action_product_dashboard')

# ── Settings page ────────────────────────────────────

@settings.page(
    id='res_config_settings_my_module',
    module='my_module',
    string='My Module',
)
def my_settings(s):
    with s.block('API Connection'):
        with s.setting('Endpoint', help='Your API credentials.'):
            s.field('api_url', readonly=True)
            s.field('api_key', password=True)
            s.button('action_test', 'Test Connection',
                     style='primary', icon='fa-plug')
    with s.block('Sync'):
        with s.setting('Auto-Sync', help='Poll automatically.'):
            s.checkbox('auto_sync')
            s.field('sync_interval', visible='auto_sync',
                    suffix='hours between syncs')
```

### 2. Compile to XML

```bash
# Single file
odoo-views compile views_dsl/product_views.py -o views/

# Entire directory
odoo-views compile views_dsl/ -o views/

# Dry run (preview without writing files)
odoo-views compile views_dsl/ --dry-run
```

Output: `views/_generated_views.xml` — standard Odoo XML, ready for `__manifest__.py`.

### 3. Reference in your manifest

```python
# __manifest__.py
{
    'data': [
        'views/_generated_views.xml',
        # ... your other XML files
    ],
}
```

That's it. The generated XML is identical to hand-written Odoo XML.

## DSL Reference

### List Views — `@view.list`

```python
@view.list(id=..., model=..., string=..., decorations={...}, editable='bottom')
def my_list(v):
    v.header_button(method, string, style='primary')
    v.column(field, string, widget=..., optional='show')
    v.badge(field, string, success='done', danger='error')
```

### Form Views — `@view.form`

```python
@view.form(id=..., model=..., string=...)
def my_form(v):
    with v.header():
        v.button(method, string, style='primary', visible=..., confirm=...)
    with v.sheet():
        v.stat_button(method, string, icon='fa-money', visible=...)
        with v.group(string, visible=..., col=2):
            v.field(name, string, widget=..., nolabel=True)
            v.badge(field, success='done')
            v.hidden('field1', 'field2')
        with v.tab(string, name=..., visible=...):
            # fields and groups inside the tab
```

### View Inheritance — `@view.form.extend` / `@view.list.extend`

```python
@view.form.extend(id=..., inherit='module.parent_view_id')
def extend(v):
    with v.inside('header'):             # → //header
        v.button(...)
    with v.inside('div[@name="..."]'):   # → //div[@name="..."]
        v.stat_button(...)
    v.after('field_name', nodes...)       # → //field[@name='...'] position=after
    v.before('field_name', nodes...)      # → position=before
    with v.tab('New Tab'):               # → //notebook position=inside
        ...
```

### Actions — `@action.window`

```python
@action.window(id=..., model=..., string=...,
               domain=[...], view_id='...', help='...',
               target='inline', context={...}, limit=80)
def my_action(a):
    a.view_list('custom_list_id')       # generates act_window.view record
    a.view_form('custom_form_id')
    a.search_field('name')
    a.search_field('partner_id')
    a.search_separator()
    a.search_filter('active', 'Active', domain=[('active','=',True)])
```

### Menus — `menu`

```python
menu.root('module_root', 'My Module', web_icon='module,static/...')
menu.item('My Module / Category / Item', action='action_id', sequence=10)
```

### Settings — `@settings.page`

```python
@settings.page(id=..., module='technical_name', string='Display Name')
def my_settings(s):
    with s.block('Section Title'):
        with s.setting('Setting Label', help='Description text.'):
            s.field('field_name', widget=..., readonly=..., password=..., placeholder=...)
            s.checkbox('bool_field')
            s.field('other_field', visible='bool_field', suffix='unit text')
            s.button('method', 'Label', style='primary', icon='fa-icon')
```

## How It Works

```
your_views.py  →  compile  →  _generated_views.xml
     DSL           Python         Standard Odoo XML
```

1. **Decorators** register definitions at import time
2. **Builders** convert DSL calls into a `Node` tree
3. **Emitter** converts `Node` trees into `xml.etree` elements
4. **Compiler** assembles everything into a valid Odoo XML file

## Running Tests

```bash
pip install -e ".[dev]"
pytest -v
```
