# Side-by-Side: Odoo XML vs DSL

Real-world examples showing the before/after for every common pattern.

---

## 1. List View with Decorations

### Odoo XML (32 lines)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="warehouse_product_dashboard_list" model="ir.ui.view">
        <field name="name">warehouse.product.dashboard.list</field>
        <field name="model">product.template</field>
        <field name="arch" type="xml">
            <list string="Warehouse Products"
                  decoration-success="readiness == 'ready'"
                  decoration-warning="readiness == 'incomplete'"
                  decoration-danger="readiness == 'no_price'">
                <header>
                    <button name="action_refresh_all"
                            type="object"
                            string="⟳ Refresh All"
                            class="btn-primary"/>
                </header>
                <field name="default_code" string="SKU"/>
                <field name="name" string="Product"/>
                <field name="readiness" string="Status" widget="badge"
                       decoration-success="readiness == 'ready'"
                       decoration-warning="readiness == 'incomplete'"
                       decoration-danger="readiness == 'no_price'"/>
                <field name="reported_qty" string="Actual"/>
                <field name="expected_qty" string="Expected"/>
                <field name="qty_discrepancy" string="Discrepancy"
                       decoration-danger="qty_discrepancy != 0"/>
                <field name="last_sync" string="Last Sync"/>
            </list>
        </field>
    </record>
</odoo>
```

### DSL (16 lines)
```python
@view.list(
    id='warehouse_product_dashboard_list',
    model='product.template',
    string='Warehouse Products',
    decorations={
        'success': "readiness == 'ready'",
        'warning': "readiness == 'incomplete'",
        'danger': "readiness == 'no_price'",
    },
)
def warehouse_product_list(v):
    v.header_button('action_refresh_all', '⟳ Refresh All', style='primary')
    v.column('default_code', 'SKU')
    v.column('name', 'Product')
    v.badge('readiness', 'Status', success='ready', warning='incomplete', danger='no_price')
    v.column('reported_qty', 'Actual')
    v.column('expected_qty', 'Expected')
    v.column('qty_discrepancy', 'Discrepancy', decoration_danger='qty_discrepancy != 0')
    v.column('last_sync', 'Last Sync')
```

**Reduction: 32 → 16 lines (50%)**

---

## 2. Form View Inheritance (Adding a Tab)

### Odoo XML (38 lines)
```xml
<record id="sale_order_form_warehouse" model="ir.ui.view">
    <field name="name">sale.order.form.warehouse</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
        <xpath expr="//header" position="inside">
            <button name="action_send_to_warehouse"
                    type="object"
                    string="Send to Warehouse"
                    class="btn-primary"
                    invisible="not has_products or order_id or state not in ('sale', 'done')"
                    confirm="Submit this order for fulfillment?"/>
        </xpath>
        <xpath expr="//div[@name='button_box']" position="inside">
            <button name="action_view_bill"
                    type="object"
                    class="oe_stat_button"
                    icon="fa-money"
                    invisible="not vendor_bill_id">
                <span class="o_stat_text">Vendor Bill</span>
            </button>
        </xpath>
        <xpath expr="//field[@name='partner_id']" position="after">
            <field name="has_products" invisible="1"/>
            <field name="order_id" invisible="1"/>
            <field name="vendor_bill_id" invisible="1"/>
        </xpath>
        <xpath expr="//notebook" position="inside">
            <page string="Warehouse" invisible="not order_id">
                <group>
                    <group string="Order">
                        <field name="order_name"/>
                        <field name="shipping_method"/>
                    </group>
                    <group string="Tracking" invisible="not tracking_info">
                        <field name="tracking_info" widget="text" nolabel="1"/>
                    </group>
                </group>
            </page>
        </xpath>
    </field>
</record>
```

### DSL (20 lines)
```python
@view.form.extend(
    id='sale_order_form_warehouse',
    inherit='sale.view_order_form',
)
def extend_sale_order(v):
    with v.inside('header'):
        v.button('action_send_to_warehouse', 'Send to Warehouse',
                 style='primary',
                 visible="has_products and not order_id and state in ('sale', 'done')",
                 confirm='Submit this order for fulfillment?')

    with v.inside('button_box'):
        v.stat_button('action_view_bill', 'Vendor Bill',
                      icon='fa-money', visible='vendor_bill_id')

    v.after('partner_id',
            v.hidden('has_products', 'order_id', 'vendor_bill_id'))

    with v.tab('Warehouse', visible='order_id'):
        with v.group('Order'):
            v.field('order_name')
            v.field('shipping_method')
        with v.group('Tracking', visible='tracking_info'):
            v.field('tracking_info', widget='text', nolabel=True)
```

**Reduction: 38 → 20 lines (47%). Zero XPath.**

---

## 3. Menu Tree

### Odoo XML (22 lines)
```xml
<menuitem id="menu_warehouse_root" name="Warehouse"
          web_icon="warehouse_module,static/description/icon.png"
          sequence="90"/>

<menuitem id="menu_warehouse_catalog" name="Catalog"
          parent="menu_warehouse_root" sequence="10"/>
<menuitem id="menu_warehouse_products" name="Products"
          parent="menu_warehouse_catalog"
          action="action_warehouse_product_dashboard" sequence="10"/>

<menuitem id="menu_warehouse_operations" name="Operations"
          parent="menu_warehouse_root" sequence="20"/>
<menuitem id="menu_warehouse_orders" name="Orders"
          parent="menu_warehouse_operations"
          action="action_warehouse_sale_orders" sequence="10"/>
<menuitem id="menu_warehouse_bills" name="Vendor Bills"
          parent="menu_warehouse_operations"
          action="action_warehouse_vendor_bills" sequence="20"/>

<menuitem id="menu_warehouse_config" name="Configuration"
          parent="menu_warehouse_root" sequence="99"/>
<menuitem id="menu_warehouse_settings" name="Settings"
          parent="menu_warehouse_config"
          action="action_warehouse_config" sequence="10"/>
```

### DSL (6 lines)
```python
menu.root('Warehouse', icon='warehouse_module,static/description/icon.png', sequence=90)
menu.item('Warehouse / Catalog / Products', action='warehouse_product_dashboard')
menu.item('Warehouse / Operations / Orders', action='warehouse_sale_orders')
menu.item('Warehouse / Operations / Vendor Bills', action='warehouse_vendor_bills')
menu.item('Warehouse / Operations / Sync Logs', action='warehouse_sync_log')
menu.item('Warehouse / Configuration / Settings', action='warehouse_config')
```

**Reduction: 22 → 6 lines (73%). Zero parent/id coordination.**

---

## 4. Settings Page

### Odoo XML (45+ lines)
```xml
<record id="res_config_settings_view_form_warehouse" model="ir.ui.view">
    <field name="name">res.config.settings.view.form.inherit.warehouse</field>
    <field name="model">res.config.settings</field>
    <field name="inherit_id" ref="base.res_config_settings_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//div[hasclass('settings')]" position="inside">
            <div class="app_settings_block" data-string="Warehouse"
                 data-key="warehouse_module"
                 groups="base.group_system">
                <block title="API Connection">
                    <setting string="Environment">
                        <div class="mt8">
                            <field name="environment" widget="radio"/>
                        </div>
                    </setting>
                    <setting string="API URL">
                        <div class="content-group">
                            <div class="row mt16">
                                <label for="api_url" class="col-lg-3 o_light_label"/>
                                <field name="api_url" class="col-lg-9"/>
                            </div>
                        </div>
                    </setting>
                    <!-- ... 20+ more lines for each field ... -->
                </block>
            </div>
        </xpath>
    </field>
</record>
```

### DSL (12 lines)
```python
@settings.page('warehouse_module', 'Warehouse')
def warehouse_settings(s):
    with s.block('API Connection'):
        s.radio('environment', [('sandbox', '🧪 Sandbox'), ('production', '🔴 Production')])
        s.field('api_url', 'API URL')
        s.field('api_key', 'API Key', widget='password')
        s.button('action_test_connection', '🔌 Test Connection', style='secondary')

    with s.block('Warehouse'):
        s.field('warehouse_location_id', 'Location')

    with s.block('Billing'):
        s.field('vendor_partner_id', 'Vendor')
        s.field('pricelist_id', 'Pricelist')
```

**Reduction: 45+ → 12 lines (73%). No CSS classes. No col-lg-3.**

---

## Summary

| Pattern | XML Lines | DSL Lines | Reduction |
|---------|-----------|-----------|-----------|
| List view with decorations | 32 | 16 | 50% |
| Form inheritance (add tab) | 38 | 20 | 47% |
| Menu tree (6 items) | 22 | 6 | 73% |
| Settings page | 45+ | 12 | 73% |
| **Typical module total** | **~200** | **~60** | **~70%** |

The XML that remains is auto-generated, validated, and identical to hand-written Odoo XML.
