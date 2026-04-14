"""Compiler — discovers DSL definitions and generates XML.

Usage::

    # CLI
    odoo-views compile path/to/module/

    # Programmatic (for testing)
    from odoo_views_dsl.compiler import compile_registry
    xml_string = compile_registry()
"""
from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path

from . import _registry
from .builders import ActionBuilder, FormViewBuilder, ListViewBuilder
from .emitter import emit_action, emit_document, emit_menuitem, emit_view


def compile_registry() -> str:
    """Compile everything currently in the global registry to an XML string.

    Returns an empty string if the registry is empty.
    """
    elements = []

    # ── Views ──
    for vdef in _registry.views:
        is_extend = bool(vdef.get('inherit'))
        builder = _make_builder(vdef['type'], extend=is_extend)
        vdef['fn'](builder)
        children = builder.build_children()
        elements.append(emit_view(vdef, children))

    # ── Actions ──
    for adef in _registry.actions:
        builder = ActionBuilder()
        if adef.get('fn'):
            adef['fn'](builder)
            if builder._views:
                # Override view_mode based on builder-declared views
                adef = {**adef, 'view_mode': builder.view_mode}

        elements.extend(emit_action(
            adef,
            search_fields=builder._search_fields or None,
            search_filters=builder._filters or None,
            default_filters=adef.get('default_filters') or None,
            view_refs=builder._views or None,
        ))

    # ── Menus ──
    elements.extend(_compile_menus(_registry.menus))

    if not elements:
        return ''
    return emit_document(elements)


def compile_module(
    source: str | Path,
    output_dir: str | Path | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, str]:
    """Compile DSL definitions found in *source* to XML files.

    Parameters
    ----------
    source : path
        A Python file or directory of Python files containing DSL definitions.
    output_dir : path, optional
        Where to write XML.  Defaults to ``<source>/views/`` (directory)
        or ``<parent>/views/`` (file).
    dry_run : bool
        If True, compile but don't write files.

    Returns
    -------
    dict
        Mapping of output filename → XML content.
    """
    source = Path(source).resolve()
    _registry.clear()

    # Import source file(s) to trigger decorator registrations
    if source.is_file():
        _import_file(source)
    elif source.is_dir():
        for py_file in sorted(source.rglob('*.py')):
            _import_file(py_file)
    else:
        raise FileNotFoundError(f'Source not found: {source}')

    xml = compile_registry()
    if not xml:
        return {}

    result = {'_generated_views.xml': xml}

    if not dry_run:
        if output_dir is None:
            base = source.parent if source.is_file() else source
            output_dir = base / 'views'
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / '_generated_views.xml').write_text(xml, encoding='utf-8')

    return result


# ─── Internal helpers ────────────────────────────────────────────────

def _make_builder(view_type: str, extend: bool = False):
    """Create the appropriate builder for a view type."""
    if view_type == 'list':
        return ListViewBuilder(extend_mode=extend)
    if view_type == 'form':
        return FormViewBuilder(extend_mode=extend)
    raise ValueError(f'Unknown view type: {view_type!r}')


def _import_file(path: Path) -> None:
    """Import a Python file to trigger DSL decorator registrations."""
    module_name = f'_odoo_dsl_tmp_.{path.stem}_{id(path)}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        warnings.warn(
            f'Could not import {path.name}: {exc}  (skipping)',
            stacklevel=2,
        )
    finally:
        sys.modules.pop(module_name, None)


def _compile_menus(menu_items: list[dict]) -> list:
    """Compile path-based menu definitions into ``<menuitem>`` elements.

    Handles:
    - Auto-creation of intermediate parent menus from slash-separated paths
    - Auto-sequencing (10, 20, 30, ...) within each parent
    - Deduplication of shared path segments across items
    """
    elements = []
    known: dict[str, str] = {}          # normalized path → xml id
    seq_counters: dict[str, int] = {}   # parent path → next sequence counter

    def _next_seq(parent_key: str) -> int:
        seq_counters.setdefault(parent_key, 0)
        seq_counters[parent_key] += 10
        return seq_counters[parent_key]

    for item in menu_items:
        if item['type'] == 'root':
            name = item['name']
            mid = f'menu_{_slugify(name)}_root'
            known[name] = mid
            elements.append(emit_menuitem({
                'id': mid,
                'name': name,
                'web_icon': item.get('icon'),
                'sequence': item.get('sequence'),
            }))

        elif item['type'] == 'item':
            parts = [p.strip() for p in item['path'].split('/')]

            for depth in range(len(parts)):
                path_key = ' / '.join(parts[:depth + 1])
                if path_key in known:
                    continue

                parent_key = ' / '.join(parts[:depth]) if depth > 0 else None
                parent_id = known.get(parent_key) if parent_key else None
                is_leaf = depth == len(parts) - 1

                # Generate XML id
                if depth == 0:
                    mid = f'menu_{_slugify(parts[0])}_root'
                else:
                    slugs = [_slugify(p) for p in parts[:depth + 1]]
                    mid = 'menu_' + '_'.join(slugs)

                seq_parent = parent_key or '__root__'
                el_def: dict = {'id': mid, 'name': parts[depth]}

                if parent_id:
                    el_def['parent'] = parent_id

                if is_leaf:
                    el_def['action'] = item.get('action')
                    el_def['sequence'] = item.get('sequence') or _next_seq(seq_parent)
                    el_def['groups'] = item.get('groups')
                else:
                    el_def['sequence'] = _next_seq(seq_parent)

                known[path_key] = mid
                elements.append(emit_menuitem(el_def))

    return elements


def _slugify(name: str) -> str:
    """Convert a display name to a valid XML-id component."""
    return name.lower().replace(' ', '_').replace('-', '_')
