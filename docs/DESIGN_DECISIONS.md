# Design Decisions

This document captures the reasoning behind key architectural choices.

---

## Why Python-to-XML Compilation (Not Runtime)

### Option A: Runtime Library (rejected)
The DSL could execute at Odoo startup, dynamically creating `ir.ui.view` records.

**Problems:**
- Requires the library installed on the Odoo server
- Breaks Odoo.sh's static module analysis
- View changes require server restart
- Debugging is harder — views exist in memory, not on disk
- Can't use standard Odoo tooling (linting, module scanner)

### Option B: Build-Time Compilation (chosen)
The DSL runs as a development tool. It reads Python files and generates standard XML.

**Benefits:**
- Zero runtime dependency
- Output is inspectable, diffable, commitable
- Works with every Odoo deployment (on-prem, Odoo.sh, Docker)
- Standard Odoo module scanner recognizes the output
- AI agents can verify the output XML

---

## Why Decorators (Not Classes)

### Option A: Class-based views (rejected)
```python
class ProductListView(ListView):
    model = 'product.template'
    fields = ['name', 'sku', 'price']
```

This mirrors Django's approach but creates tension with Odoo's model system — you'd have model classes AND view classes, each referencing the other.

### Option B: Decorator-based views (chosen)
```python
@view.list(model='product.template')
def product_list(v):
    v.column('name', 'Product')
```

**Benefits:**
- Views are functions, not classes — lighter mental model
- Can live inside the model file or separately
- The `v` builder pattern reads top-to-bottom like the final UI
- Familiar to developers who've used Flask/FastAPI

---

## Why Path-Based Menus

### Odoo's approach: explicit parent chains
```xml
<menuitem id="menu_root" name="App"/>
<menuitem id="menu_catalog" parent="menu_root" name="Catalog"/>
<menuitem id="menu_products" parent="menu_catalog" action="..." name="Products"/>
```

Three records for one menu path. IDs must be manually coordinated.

### DSL approach: filesystem-style paths
```python
menu.item('App / Catalog / Products', action='product_list')
```

One line. Intermediate parents are auto-created. IDs are auto-generated from the path (`menu_app_root`, `menu_app_catalog`, `menu_app_catalog_products`). Overridable if needed.

---

## Why Context Managers for Grouping

### Form view groups use Python's `with` statement:
```python
with v.group('Billing'):
    v.field('partner_id')
    v.field('payment_term_id')
```

This maps directly to XML's nested structure:
```xml
<group string="Billing">
    <field name="partner_id"/>
    <field name="payment_term_id"/>
</group>
```

**Why `with`:**
- Visual indentation matches the XML nesting
- Python enforces proper closing (no forgotten `</group>`)
- Reads naturally: "within the Billing group, show these fields"

---

## Handling `&lt;` and Special Characters

XML requires escaping `<` as `&lt;` in attribute values. This is a constant source of bugs:
```xml
<!-- Easy to forget -->
decoration-danger="qty &lt; 0"
```

The DSL handles this automatically:
```python
v.column('qty', decoration_danger='qty < 0')
# Compiler emits: decoration-danger="qty &lt; 0"
```

Developers write natural Python expressions. The compiler handles escaping.

---

## Generated File Strategy

### Option A: Generate into `views/` directory (chosen for now)
```
my_module/
├── models/
│   └── product.py        # Source of truth (Python + DSL)
└── views/
    └── product_views.xml  # Generated (can be gitignored or committed)
```

**Committed approach:** The XML is checked into git alongside the Python source. CI validates they're in sync. Odoo.sh works without any build step.

**Gitignored approach:** Only the Python source is committed. A build step generates XML before deployment. Cleaner diffs but requires build infrastructure.

Both are supported. The recommended approach depends on the deployment target.

### Option B: Generate into `_generated/` subdirectory
```
my_module/
├── models/
│   └── product.py
└── _generated/
    └── product_views.xml
```

Clearer separation but requires updating `__manifest__.py` to include the `_generated` path.

---

## Incremental Adoption

The DSL is designed for gradual adoption within existing modules:

1. **New views** → Write in Python, compile to XML
2. **Existing views** → Leave as XML, untouched
3. **Mixed module** → Some views in Python, some in XML, both work

The compiler only processes files with DSL decorators. It never touches existing XML files.

---

## Supported Odoo Versions

The compiler targets Odoo 17, 18, and 19+. Version differences are handled by the emitter:

| Feature | Odoo 17 | Odoo 18+ |
|---------|---------|----------|
| `invisible` attribute | `attrs="{'invisible': [...]}"` | `invisible="expression"` |
| `readonly` attribute | `attrs="{'readonly': [...]}"` | `readonly="expression"` |
| `required` attribute | `attrs="{'required': [...]}"` | `required="expression"` |

The DSL always uses the modern syntax. The compiler emits the correct format based on a `target_version` setting:

```python
# In __manifest__.py or compiler config
'odoo_views_dsl': {
    'target_version': 18,
}
```

---

## Comparison with Existing Tools

| Tool | Approach | Scope |
|------|----------|-------|
| **odoo-views-dsl** | Python decorators → XML | Views, menus, actions |
| [OCA/odoo-pre-commit-hooks](https://github.com/OCA/odoo-pre-commit-hooks) | Lint existing XML | Validation only |
| [odoo-stubs](https://github.com/trevi-software/odoo-stubs) | Type hints for Odoo | IDE support only |
| Manual XML | Write by hand | Everything |

None of the existing tools address the authoring experience. This project fills that gap.
