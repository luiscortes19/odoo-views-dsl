"""Generate Odoo-compatible XML from Node trees and definitions.

This module converts the internal ``Node`` tree representation into
``xml.etree.ElementTree`` elements, then assembles them into a complete
Odoo XML data file.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .nodes import Node


# ─── XPath helpers ───────────────────────────────────────────────────

def _resolve_xpath_target(target: str) -> str:
    """Convert a DSL target string to an XPath expression.

    - ``'header'`` → ``//header``
    - ``'div[@name="button_box"]'`` → ``//div[@name="button_box"]``
    - ``'//custom/path'`` → ``//custom/path`` (pass-through)
    """
    if target.startswith('/'):
        return target
    return f'//{target}'


# ─── Node → Element ─────────────────────────────────────────────────

def _node_to_element(node: Node) -> ET.Element:
    """Recursively convert a Node to an ElementTree Element.

    Handles ``_xpath_*`` marker nodes by converting them to proper
    ``<xpath>`` elements with the correct ``expr`` and ``position``.
    """
    # ── XPath markers (view inheritance) ──
    if node.tag == '_xpath_inside':
        expr = _resolve_xpath_target(node.attrs['target'])
        elem = ET.Element('xpath', {'expr': expr, 'position': 'inside'})
        for child in node.children:
            elem.append(_node_to_element(child))
        return elem

    if node.tag == '_xpath_after':
        field_name = node.attrs['target']
        elem = ET.Element('xpath', {
            'expr': f"//field[@name='{field_name}']",
            'position': 'after',
        })
        for child in node.children:
            elem.append(_node_to_element(child))
        return elem

    if node.tag == '_xpath_before':
        field_name = node.attrs['target']
        elem = ET.Element('xpath', {
            'expr': f"//field[@name='{field_name}']",
            'position': 'before',
        })
        for child in node.children:
            elem.append(_node_to_element(child))
        return elem

    # ── Regular elements ──
    elem = ET.Element(node.tag, node.attrs)
    if node.text is not None:
        elem.text = node.text
    for child in node.children:
        elem.append(_node_to_element(child))
    return elem


# ─── View records ────────────────────────────────────────────────────

def emit_view(view_def: dict, children: list[Node]) -> ET.Element:
    """Emit a single ``<record model="ir.ui.view">`` element."""
    view_id = view_def['id']
    view_type = view_def['type']       # 'list' or 'form'
    string = view_def.get('string', '')
    model = view_def.get('model')
    is_inherited = bool(view_def.get('inherit'))

    record = ET.Element('record', {'id': view_id, 'model': 'ir.ui.view'})

    # <field name="name">
    ET.SubElement(record, 'field', {'name': 'name'}).text = (
        view_id.replace('_', '.')
    )

    # <field name="model"> (optional for inherited views)
    if model:
        ET.SubElement(record, 'field', {'name': 'model'}).text = model

    # <field name="inherit_id">
    if is_inherited:
        ET.SubElement(record, 'field', {
            'name': 'inherit_id',
            'ref': view_def['inherit'],
        })

    # <field name="priority">
    if view_def.get('priority') is not None:
        ET.SubElement(record, 'field', {'name': 'priority'}).text = str(
            view_def['priority']
        )

    # <field name="arch" type="xml">
    arch = ET.SubElement(record, 'field', {'name': 'arch', 'type': 'xml'})

    if is_inherited:
        # Inherited view: arch contains xpath operations directly
        # (no <form>/<list> wrapper)
        for child in children:
            arch.append(_node_to_element(child))
    else:
        # Standalone view: wrap children in <form>/<list> root element
        root_attrs: dict[str, str] = {}
        if string:
            root_attrs['string'] = string

        # List-specific: row decorations
        if view_type == 'list':
            decorations = view_def.get('decorations') or {}
            for level, expr in decorations.items():
                root_attrs[f'decoration-{level}'] = expr
            if view_def.get('editable'):
                root_attrs['editable'] = view_def['editable']

        root_el = ET.SubElement(arch, view_type, root_attrs)
        for child in children:
            root_el.append(_node_to_element(child))

    return record


def emit_action(
    action_def: dict,
    *,
    search_fields: list[dict] | None = None,
    search_filters: list[dict] | None = None,
    default_filters: dict | None = None,
    view_refs: list[dict] | None = None,
) -> list[ET.Element]:
    """Emit action record(s).  May include companion records.

    Returns a list because a single ``@action.window`` can produce:

    - A search-view record (when filters/search fields are defined)
    - The main act_window record
    - ``ir.actions.act_window.view`` records (when specific views are bound)
    """
    elements: list[ET.Element] = []
    action_id = action_def['id']
    has_search = bool(search_fields or search_filters)

    # ── Search view ──
    if has_search:
        search_id = f'{action_id}_search'
        srec = ET.Element('record', {'id': search_id, 'model': 'ir.ui.view'})
        ET.SubElement(srec, 'field', {'name': 'name'}).text = (
            search_id.replace('_', '.')
        )
        ET.SubElement(srec, 'field', {'name': 'model'}).text = action_def['model']
        arch = ET.SubElement(srec, 'field', {'name': 'arch', 'type': 'xml'})
        search_el = ET.SubElement(arch, 'search')

        # Searchable fields
        for sf in (search_fields or []):
            if sf.get('_separator'):
                ET.SubElement(search_el, 'separator')
            else:
                sf_attrs = {'name': sf['name']}
                for k, v in sf.items():
                    if k != 'name':
                        sf_attrs[k] = str(v)
                ET.SubElement(search_el, 'field', sf_attrs)

        # Filters
        for f in (search_filters or []):
            f_attrs: dict[str, str] = {
                'name': f['name'],
                'string': f['string'],
            }
            if f.get('domain'):
                f_attrs['domain'] = str(f['domain'])
            ET.SubElement(search_el, 'filter', f_attrs)
        elements.append(srec)

    # ── act_window record ──
    record = ET.Element('record', {'id': action_id, 'model': 'ir.actions.act_window'})
    ET.SubElement(record, 'field', {'name': 'name'}).text = action_def.get(
        'string', action_id
    )
    ET.SubElement(record, 'field', {'name': 'res_model'}).text = action_def['model']
    ET.SubElement(record, 'field', {'name': 'view_mode'}).text = action_def.get(
        'view_mode', 'list,form'
    )

    if action_def.get('domain'):
        ET.SubElement(record, 'field', {'name': 'domain'}).text = str(
            action_def['domain']
        )

    # Context — includes search_default_* for default filters
    ctx: dict = {}
    if default_filters:
        for k, v in default_filters.items():
            ctx[f'search_default_{k}'] = v
    if action_def.get('context'):
        ctx.update(action_def['context'])
    if ctx:
        ET.SubElement(record, 'field', {'name': 'context'}).text = str(ctx)

    # Target (current, new, inline, fullscreen)
    if action_def.get('target'):
        ET.SubElement(record, 'field', {'name': 'target'}).text = (
            action_def['target']
        )

    # Default view_id ref
    if action_def.get('view_id'):
        ET.SubElement(record, 'field', {
            'name': 'view_id',
            'ref': action_def['view_id'],
        })

    if has_search:
        ET.SubElement(record, 'field', {
            'name': 'search_view_id',
            'ref': f'{action_id}_search',
        })

    if action_def.get('limit'):
        ET.SubElement(record, 'field', {'name': 'limit'}).text = str(
            action_def['limit']
        )

    # Help text — smiling face empty-state pattern
    if action_def.get('help'):
        help_field = ET.SubElement(record, 'field', {
            'name': 'help', 'type': 'html',
        })
        p = ET.SubElement(help_field, 'p', {
            'class': 'o_view_nocontent_smiling_face',
        })
        p.text = action_def['help']

    elements.append(record)

    # ── ir.actions.act_window.view records ──
    for seq, vref in enumerate(view_refs or [], start=1):
        vrec = ET.Element('record', {
            'id': f'{action_id}_{vref["type"]}',
            'model': 'ir.actions.act_window.view',
        })
        ET.SubElement(vrec, 'field', {'name': 'sequence'}).text = str(seq)
        ET.SubElement(vrec, 'field', {'name': 'view_mode'}).text = vref['type']
        ET.SubElement(vrec, 'field', {
            'name': 'view_id', 'ref': vref['id'],
        })
        ET.SubElement(vrec, 'field', {
            'name': 'act_window_id', 'ref': action_id,
        })
        elements.append(vrec)

    return elements


# ─── Menu items ──────────────────────────────────────────────────────

def emit_menuitem(menu_def: dict) -> ET.Element:
    """Emit a single ``<menuitem>`` element."""
    attrs: dict[str, str] = {
        'id': menu_def['id'],
        'name': menu_def['name'],
    }
    if menu_def.get('parent'):
        attrs['parent'] = menu_def['parent']
    if menu_def.get('action'):
        attrs['action'] = menu_def['action']
    if menu_def.get('sequence') is not None:
        attrs['sequence'] = str(menu_def['sequence'])
    if menu_def.get('web_icon'):
        attrs['web_icon'] = menu_def['web_icon']
    if menu_def.get('groups'):
        attrs['groups'] = menu_def['groups']
    return ET.Element('menuitem', attrs)


# ─── Document assembly ──────────────────────────────────────────────

def emit_document(elements: list[ET.Element]) -> str:
    """Wrap elements in ``<odoo>`` and return a formatted XML string."""
    odoo = ET.Element('odoo')
    for el in elements:
        odoo.append(el)
    ET.indent(odoo, space='    ')
    xml_body = ET.tostring(odoo, encoding='unicode', xml_declaration=False)
    return f'<?xml version="1.0" encoding="utf-8"?>\n{xml_body}\n'
