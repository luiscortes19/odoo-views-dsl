# odoo-views-dsl

**Python-native view DSL for Odoo** — write views, menus, and actions in Python. Never touch `<record>` / `<field>` XML again.

> ⚠️ **Status: Design Phase** — This repo captures the architecture and design decisions. Implementation is planned.

---

## The Problem

Odoo modules require views, menus, and actions to be defined in XML using a generic `<record>` + `<field>` pattern. This creates several pain points:

### 1. Verbose Boilerplate
A simple list view requires 30+ lines of XML wrapping for what is essentially "show these 5 fields in a table":

```xml
<!-- What you write today: 25 lines -->
<record id="my_product_list" model="ir.ui.view">
    <field name="name">my.product.list</field>
    <field name="model">product.template</field>
    <field name="arch" type="xml">
        <list string="Products">
            <field name="name" string="Product"/>
            <field name="default_code" string="SKU"/>
            <field name="list_price" string="Price"/>
        </list>
    </field>
</record>
```

```python
# What you should write: 5 lines
@view.list('Products')
def product_list(v):
    v.column('name', 'Product')
    v.column('default_code', 'SKU')
    v.column('list_price', 'Price')
```

### 2. Fragile Inheritance
View inheritance relies on XPath expressions that break silently when parent views change:

```xml
<!-- Today: hope the XPath matches something -->
<xpath expr="//field[@name='phone']" position="after">
    <field name="custom_field"/>
</xpath>
```

```python
# DSL: explicit, refactor-safe
@view.form.extend('sale.view_order_form')
def extend_sale_form(v):
    v.after('phone', v.field('custom_field'))
```

### 3. Scattered Context
Understanding a single feature requires jumping between 3-5 files:
```
models/product.py         → field definitions
views/product_views.xml   → form/list views
views/menus.xml           → menu items  
views/actions.xml         → window actions
security/ir.model.access.csv → permissions
```

With the DSL, everything lives together:
```
models/product.py → fields + views + menus + actions
```

### 4. Agent-Hostile Format
AI coding agents generate more bugs in XML than Python:
- Wrong XPath expressions
- Mismatched closing tags
- Forgotten `&lt;` escaping
- References to non-existent action IDs

More importantly, **human reviewers** struggle to verify XML diffs. In an agent-driven workflow, the format that maximizes human auditability wins.

---

## Architecture

```
┌──────────────────────┐
│   Developer writes   │
│   Python decorators  │
│   (model + views)    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   odoo_views_dsl     │
│   compiler           │
│   (Python → XML)     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Standard Odoo XML  │
│   (views, menus,     │
│    actions, data)    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Odoo / Odoo.sh     │
│   (unchanged)        │
└──────────────────────┘
```

The compiler runs at **build time** (pre-commit hook, CI, or manual). Odoo receives standard XML it already understands. Zero runtime changes. Zero Odoo patches.

---

## DSL Design

### Models (unchanged)
```python
from odoo import api, fields, models

class WarehouseProduct(models.Model):
    _inherit = 'product.template'

    is_warehouse = fields.Boolean(compute='_compute_is_warehouse', store=True)
    warehouse_qty = fields.Float('Warehouse Qty', compute='_compute_qty')
    readiness = fields.Selection([
        ('ready', 'Ready'),
        ('incomplete', 'Incomplete'),
    ], compute='_compute_readiness', store=True)
```

### List Views
```python
from odoo_views_dsl import view

@view.list(
    id='warehouse_product_list',
    model='product.template',
    string='Warehouse Products',
    domain=[('is_warehouse', '=', True)],
    decorations={
        'success': "readiness == 'ready'",
        'danger': "readiness == 'incomplete'",
    },
)
def warehouse_product_list(v):
    v.header_button('action_refresh_all', '⟳ Refresh All', style='primary')
    v.column('default_code', 'SKU')
    v.column('name', 'Product')
    v.badge('readiness', 'Status', success='ready', danger='incomplete')
    v.column('warehouse_qty', 'Qty', decoration_danger='warehouse_qty < 0')
    v.column('last_sync', 'Last Sync')
```

**Compiles to:**
```xml
<record id="warehouse_product_list" model="ir.ui.view">
    <field name="name">warehouse.product.list</field>
    <field name="model">product.template</field>
    <field name="arch" type="xml">
        <list string="Warehouse Products"
              decoration-success="readiness == 'ready'"
              decoration-danger="readiness == 'incomplete'">
            <header>
                <button name="action_refresh_all" type="object"
                        string="⟳ Refresh All" class="btn-primary"/>
            </header>
            <field name="default_code" string="SKU"/>
            <field name="name" string="Product"/>
            <field name="readiness" string="Status" widget="badge"
                   decoration-success="readiness == 'ready'"
                   decoration-danger="readiness == 'incomplete'"/>
            <field name="warehouse_qty" string="Qty"
                   decoration-danger="warehouse_qty &lt; 0"/>
            <field name="last_sync" string="Last Sync"/>
        </list>
    </field>
</record>
```

### Form Views
```python
@view.form(
    id='warehouse_product_form',
    model='product.template',
    inherit='product.product_template_only_form_view',
)
def warehouse_product_form(v):
    with v.tab('Warehouse', visible="is_warehouse"):
        with v.group('Readiness'):
            v.badge('readiness', success='ready', danger='incomplete')
            v.field('readiness_notes', visible="readiness != 'ready'")
        with v.group('Inventory'):
            v.field('warehouse_qty')
            v.field('expected_qty')
            v.field('discrepancy', decoration_danger='discrepancy != 0')
        v.button('action_refresh', '🔄 Refresh from Warehouse', style='primary')
```

### Menus
```python
from odoo_views_dsl import menu

menu.root('Warehouse', icon='warehouse_module,static/description/icon.png', sequence=90)
menu.item('Warehouse / Catalog / Products', action='warehouse_product_list')
menu.item('Warehouse / Operations / Orders', action='warehouse_sale_orders')
menu.item('Warehouse / Operations / Vendor Bills', action='warehouse_vendor_bills')
menu.item('Warehouse / Configuration / Settings', action='warehouse_config')
```

**Compiles to:**
```xml
<menuitem id="menu_warehouse_root" name="Warehouse"
          web_icon="warehouse_module,static/description/icon.png" sequence="90"/>
<menuitem id="menu_warehouse_catalog" name="Catalog"
          parent="menu_warehouse_root" sequence="10"/>
<menuitem id="menu_warehouse_catalog_products" name="Products"
          parent="menu_warehouse_catalog" action="warehouse_product_list" sequence="10"/>
<!-- ... etc ... -->
```

### Actions
```python
from odoo_views_dsl import action

@action.window(
    id='warehouse_sale_orders',
    model='sale.order',
    string='Warehouse Orders',
    domain=[('has_warehouse_products', '=', True)],
    default_filters={'submitted': 1},
)
def warehouse_orders(a):
    a.view_list('warehouse_sale_order_list')
    a.search_filter('not_submitted', 'Not Yet Submitted',
                    domain=[('order_id', '=', False)])
    a.search_filter('submitted', 'Submitted',
                    domain=[('order_id', '!=', False)])
```

### Settings
```python
from odoo_views_dsl import settings

@settings.page('warehouse_module', 'Warehouse')
def warehouse_settings(s):
    with s.block('API Connection'):
        s.radio('environment', [
            ('sandbox', '🧪 Sandbox'),
            ('production', '🔴 Production'),
        ], onchange='_onchange_environment')
        s.field('api_url', 'API URL')
        s.field('api_key', 'API Key', widget='password')
        s.button('action_test_connection', '🔌 Test Connection', style='secondary')

    with s.block('Warehouse'):
        s.field('warehouse_location_id', 'Warehouse Location')

    with s.block('Billing'):
        s.field('vendor_partner_id', 'Vendor')
        s.field('pricelist_id', 'Pricelist')
```

### View Inheritance
```python
@view.form.extend(
    id='sale_order_form_warehouse',
    inherit='sale.view_order_form',
)
def extend_sale_order(v):
    # Header buttons
    with v.inside('header'):
        v.button('action_send_to_warehouse', 'Send to Warehouse',
                 style='primary',
                 visible="has_warehouse_products and not order_id and state in ('sale', 'done')",
                 confirm='Submit this order to the warehouse?')

    # Smart buttons
    with v.inside('div[@name="button_box"]'):
        v.stat_button('action_view_bill', 'Vendor Bill',
                      icon='fa-money', visible='vendor_bill_id')

    # Hidden fields
    v.after('partner_id',
            v.hidden('has_warehouse_products'),
            v.hidden('order_id'),
            v.hidden('vendor_bill_id'))

    # New tab
    with v.tab('Warehouse', visible='order_id'):
        with v.group('Order'):
            v.field('order_name')
            v.field('shipping_method')
        with v.group('Tracking', visible='tracking_info'):
            v.field('tracking_info', widget='text', nolabel=True)
```

**Compiles to the equivalent `<xpath>` operations automatically.** No XPath strings to memorize or debug.

---

## Compilation

### CLI
```bash
# Compile a single module
odoo-views compile my_module/

# Compile and watch for changes
odoo-views watch my_module/

# Validate without writing (dry run)
odoo-views check my_module/
```

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/luiscortes19/odoo-views-dsl
    hooks:
      - id: odoo-views-compile
        files: ^.*\.py$
```

### Odoo.sh Integration
Add to the build script so XML is generated before Odoo starts:
```bash
pip install odoo-views-dsl
odoo-views compile custom_addons/
```

---

## Design Principles

1. **Zero runtime dependency** — Output is standard Odoo XML. The DSL is a dev tool, not a runtime library.
2. **100% Odoo compatible** — Every XML feature is supported. Anything the DSL can't express can be written as raw XML alongside it.
3. **Convention over configuration** — IDs, names, and parent references are auto-generated from context but overridable.
4. **One file per feature** — Models, views, menus, and actions for a feature live together.
5. **Agent-friendly** — Python is easier for AI agents to generate correctly and for humans to review.
6. **Incremental adoption** — Use the DSL for new views. Existing XML files work unchanged.

---

## Non-Goals

- **Replacing Odoo's ORM** — `fields.Char`, `@api.depends`, etc. are fine as-is.
- **Runtime view manipulation** — This is a compile-time tool, not a runtime engine.
- **Supporting non-Odoo frameworks** — Purpose-built for Odoo 17/18/19+.

---

## Project Structure
```
odoo_views_dsl/
├── __init__.py          # Public API exports
├── compiler.py          # Python AST → XML generator
├── view.py              # @view.list, @view.form decorators
├── menu.py              # menu.root, menu.item helpers
├── action.py            # @action.window decorator
├── settings.py          # @settings.page decorator
├── emitters/
│   ├── xml_emitter.py   # Generates Odoo-compatible XML
│   └── validator.py     # Validates references and structure
├── cli.py               # CLI entry point
└── tests/
    ├── test_list_view.py
    ├── test_form_view.py
    ├── test_menu.py
    └── test_inheritance.py

examples/
├── warehouse_module/         # Complete example module
│   ├── __manifest__.py
│   ├── models/
│   │   └── product.py        # Model + views + menus in one file
│   └── views/
│       └── _generated.xml    # Auto-generated (gitignored or committed)
└── crm_extension/            # Example of extending standard Odoo views
    └── models/
        └── crm_lead.py
```

---

## Roadmap

- [ ] **Phase 1: Core Compiler** — list views, form views, basic fields
- [ ] **Phase 2: Inheritance** — `@view.form.extend`, XPath generation
- [ ] **Phase 3: Menus & Actions** — full menu tree, window actions, filters
- [ ] **Phase 4: Settings Pages** — `res.config.settings` view generation
- [ ] **Phase 5: CLI & Hooks** — compile, watch, pre-commit, Odoo.sh integration
- [ ] **Phase 6: Validation** — field name checking, action reference verification

---

## License

MIT
