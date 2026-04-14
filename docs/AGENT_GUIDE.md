# Agent Guide — odoo-views-dsl

> This guide is written for AI coding agents (Gemini, Claude, Copilot, etc.)
> that need to create or modify Odoo views programmatically.  It provides
> the complete mapping from Odoo XML patterns to Python DSL calls.

## Why This Tool Exists

Odoo modules traditionally split logic across two places:
- **`models/sale_order.py`** — Python ORM model
- **`views/sale_order_views.xml`** — XML view definitions

This means every change requires editing two files in two languages.
`odoo-views-dsl` lets you write views in Python, **co-located right next
to the model they describe**, and compiles them to standard Odoo XML.

## Module Layout (Co-located Pattern)

```
my_module/
├── __manifest__.py              # references views/_generated_views.xml
├── models/
│   ├── __init__.py              # imports ONLY Odoo model files
│   ├── sale_order.py            # Odoo ORM model
│   ├── sale_order_views.py      # ← DSL views for sale_order
│   ├── product_template.py      # Odoo ORM model
│   ├── product_template_views.py # ← DSL views for product_template
│   ├── my_new_model.py          # Odoo ORM model (custom)
│   ├── my_new_model_views.py    # ← DSL views for my_new_model
│   └── _menus.py                # ← module-wide menu tree
├── views/
│   └── _generated_views.xml     # ← compiled output (DO NOT EDIT)
└── ...
```

### Key Rules

1. **DSL files use `_views.py` suffix** — paired with their model file
2. **Menus go in `_menus.py`** — the menu tree is module-wide, not per-model
3. **`__init__.py` does NOT import `_views.py` files** — Odoo ignores them
4. **The compiler scans `models/`** and silently skips Odoo model files
5. **`_generated_views.xml` is committed to git** — Odoo.sh has no build step

### Compile Command

```bash
odoo-views compile models/ -o views/
```

## Complete XML → DSL Reference

### Standalone List View

XML:
```xml
<record id="my_list" model="ir.ui.view">
    <field name="name">my.list</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <list string="My Records"
              decoration-success="state == 'done'"
              default_order="create_date desc">
            <header>
                <button name="action_do" type="object" string="Do It" class="btn-primary"/>
            </header>
            <field name="name" string="Name"/>
            <field name="state" widget="badge"
                   decoration-success="state == 'done'"
                   decoration-danger="state == 'error'"/>
            <field name="amount" sum="Total"/>
            <field name="secret" optional="hide"/>
            <field name="internal_flag" column_invisible="True"/>
        </list>
    </field>
</record>
```

DSL:
```python
@view.list(
    id='my_list',
    model='my.model',
    string='My Records',
    decorations={'success': "state == 'done'"},
    default_order='create_date desc',
)
def my_list(v):
    v.header_button('action_do', 'Do It', style='primary')
    v.column('name', 'Name')
    v.badge('state', success='done', danger='error')
    v.column('amount', sum='Total')
    v.column('secret', optional='hide')
    v.column('internal_flag', column_invisible='True')
```

### Standalone Form View

XML:
```xml
<form string="My Record" create="0" edit="0">
    <header>
        <button name="action_confirm" type="object" string="Confirm"
                class="btn-primary"
                invisible="state != 'draft'"
                confirm="Are you sure?"/>
    </header>
    <sheet>
        <div class="oe_button_box" name="button_box">
            <button name="action_view_orders" type="object"
                    class="oe_stat_button" icon="fa-list"
                    invisible="order_count == 0">
                <span class="o_stat_text">Orders</span>
            </button>
        </div>
        <group>
            <group string="General">
                <field name="name"/>
                <field name="partner_id"/>
            </group>
            <group string="Amounts">
                <field name="amount" widget="monetary"/>
            </group>
        </group>
        <notebook>
            <page string="Details" invisible="not detail_ids">
                <field name="detail_ids"/>
            </page>
        </notebook>
    </sheet>
</form>
```

DSL:
```python
@view.form(
    id='my_form',
    model='my.model',
    string='My Record',
    create='0',
    edit='0',
)
def my_form(v):
    with v.header():
        v.button('action_confirm', 'Confirm', style='primary',
                 visible="state == 'draft'",
                 confirm='Are you sure?')
    with v.sheet():
        v.stat_button('action_view_orders', 'Orders',
                      icon='fa-list', visible='order_count != 0')
        with v.group():
            with v.group('General'):
                v.field('name')
                v.field('partner_id')
            with v.group('Amounts'):
                v.field('amount', widget='monetary')
        with v.tab('Details', visible='detail_ids'):
            v.field('detail_ids')
```

### Inherited Form View (XPath)

XML:
```xml
<record id="my_form_extend" model="ir.ui.view">
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
        <xpath expr="//header" position="inside">
            <button name="action_custom" type="object" string="Custom"
                    class="btn-primary"/>
        </xpath>
        <xpath expr="//div[@name='button_box']" position="inside">
            <button name="action_view_bill" type="object"
                    class="oe_stat_button" icon="fa-money">
                <span class="o_stat_text">Bill</span>
            </button>
        </xpath>
        <xpath expr="//field[@name='partner_id']" position="after">
            <field name="custom_ref" invisible="1"/>
        </xpath>
        <xpath expr="//notebook" position="inside">
            <page string="Custom Tab" invisible="not custom_ref">
                <group string="Custom">
                    <field name="custom_field"/>
                </group>
            </page>
        </xpath>
    </field>
</record>
```

DSL:
```python
@view.form.extend(
    id='my_form_extend',
    inherit='sale.view_order_form',
    model='sale.order',          # ⚠️ REQUIRED — Odoo crashes without this
)
def extend_sale_order(v):
    with v.inside('header'):
        v.button('action_custom', 'Custom', style='primary')

    with v.inside('div[@name="button_box"]'):
        v.stat_button('action_view_bill', 'Bill', icon='fa-money')

    v.after('partner_id', v.hidden('custom_ref'))

    with v.tab('Custom Tab', visible='custom_ref'):
        with v.group('Custom'):
            v.field('custom_field')
```

### Inherited List View (XPath)

```python
@view.list.extend(
    id='partner_list_custom',
    inherit='base.view_partner_list',
    model='res.partner',         # ⚠️ REQUIRED
)
def extend_partner_list(v):
    v.after('name', v.make_field('custom_field', 'Custom'))
```

### Window Action + Search View

XML:
```xml
<record id="my_search" model="ir.ui.view">
    <field name="arch" type="xml">
        <search>
            <field name="name"/>
            <field name="partner_id"/>
            <separator/>
            <filter name="active" string="Active"
                    domain="[('active','=',True)]"/>
        </search>
    </field>
</record>
<record id="my_action" model="ir.actions.act_window">
    <field name="name">My Records</field>
    <field name="res_model">my.model</field>
    <field name="domain">[('type','=','custom')]</field>
    <field name="context">{'search_default_active': 1}</field>
    <field name="search_view_id" ref="my_search"/>
</record>
<record id="my_action_list" model="ir.actions.act_window.view">
    <field name="sequence">1</field>
    <field name="view_mode">list</field>
    <field name="view_id" ref="my_list"/>
    <field name="act_window_id" ref="my_action"/>
</record>
```

DSL (generates ALL THREE records above):
```python
@action.window(
    id='my_action',
    model='my.model',
    string='My Records',
    domain=[('type', '=', 'custom')],
    default_filters={'active': 1},
)
def my_action(a):
    a.view_list('my_list')           # → act_window.view record
    a.search_field('name')           # → search view fields
    a.search_field('partner_id')
    a.search_separator()
    a.search_filter('active', 'Active',
                    domain=[('active', '=', True)])
```

### Simple Actions (no search view)

```python
@action.window(
    id='action_vendor_bills',
    model='account.move',
    string='Vendor Bills',
    domain=[('move_type', '=', 'in_invoice')],
    context={'default_move_type': 'in_invoice'},
)
def vendor_bills(a):
    pass                              # no search/views to configure

# Settings action (inline form)
@action.window(
    id='action_settings',
    model='res.config.settings',
    string='My Settings',
    view_mode='form',
    target='inline',
    context={'module': 'my_module'},
)
def settings_action(a):
    pass
```

### Menus

XML:
```xml
<menuitem id="menu_root" name="My App"
          web_icon="my_module,static/description/icon.png" sequence="90"/>
<menuitem id="menu_catalog" name="Catalog" parent="menu_root"/>
<menuitem id="menu_products" name="Products" parent="menu_catalog"
          action="action_products" sequence="10"/>
```

DSL:
```python
menu.root('My App', icon='my_module,static/description/icon.png', sequence=90)
menu.item('My App / Catalog / Products', action='action_products', sequence=10)
# ↑ Intermediate parent menus are auto-created from the path
```

### Settings Page (res.config.settings)

XML (extremely verbose — 50+ lines of `<div class="row mt8"><label/><field/></div>`):

DSL:
```python
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
            s.checkbox('auto_sync')              # checkbox toggle
            s.field('sync_interval',
                    visible='auto_sync',          # conditional field
                    suffix='hours between syncs') # text after field
```

## Quick Reference Card

| XML Pattern | DSL Call |
|---|---|
| `<field name="x"/>` | `v.field('x')` or `v.column('x')` |
| `<field name="x" widget="badge"/>` | `v.badge('x', success='done')` |
| `<field name="x" invisible="1"/>` | `v.hidden('x')` or `v.field('x', invisible='1')` |
| `<button name="m" class="btn-primary"/>` | `v.button('m', 'Label', style='primary')` |
| `<button class="oe_stat_button"/>` | `v.stat_button('m', 'Label', icon='fa-x')` |
| `invisible="expr"` | `visible="inverse_expr"` (auto-negated) |
| `<header>` | `with v.header():` |
| `<sheet>` | `with v.sheet():` |
| `<group string="X">` | `with v.group('X'):` |
| `<notebook><page string="X">` | `with v.tab('X'):` |
| `<xpath expr="//X" position="inside">` | `with v.inside('X'):` |
| `<xpath expr="//field[@name='x']" position="after">` | `v.after('x', ...)` |
| `<xpath expr="//field[@name='x']" position="before">` | `v.before('x', ...)` |

## Gotchas

0. **⚠️ `model=` is REQUIRED on `extend()`**: Every `@view.form.extend` and
   `@view.list.extend` call MUST include `model='the.model.name'`. Without it,
   Odoo crashes with `Model not found: False` during module installation.
   The `model` parameter is technically optional in the DSL (for flexibility),
   but Odoo itself requires `<field name="model">` on inherited view records.

1. **`visible` vs `invisible`**: The DSL uses `visible=` which auto-negates to
   Odoo's `invisible=`. If you need the raw `invisible=` expression, pass
   `invisible="expr"` directly.

2. **`v.column()` vs `v.field()`**: Use `column()` in list views, `field()` in
   form views. Both emit `<field>` but `column()` lives on `ListViewBuilder`.

3. **`badge()` shorthand**: `v.badge('state', success='done', danger='error')`
   auto-generates `decoration-success="state == 'done'"` etc.

4. **Settings `field()` generates label+row**: Unlike `v.field()` in forms,
   `s.field()` in settings generates the full
   `<div class="row"><label/><field/></div>` pattern.

5. **Menu paths auto-create parents**: `menu.item('A / B / C', action='x')`
   creates menu `A`, menu `A > B`, and leaf `A > B > C` automatically.

6. **XML escaping is automatic**: Pass raw `<`, `>`, `&` in Python strings.
   The XML serializer handles escaping.

7. **Compiler skips Odoo files**: When pointed at `models/`, files that
   `import odoo` fail gracefully — only `_views.py` files are processed.
