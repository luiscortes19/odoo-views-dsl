"""Builder classes — the objects passed to decorated DSL functions.

ListViewBuilder    → the ``v`` in ``@view.list``
FormViewBuilder    → the ``v`` in ``@view.form``
ActionBuilder      → the ``a`` in ``@action.window``
SettingsBuilder    → the ``s`` in ``@settings.page``
"""
from __future__ import annotations

from contextlib import contextmanager

from .nodes import Node


# ─── Helpers ─────────────────────────────────────────────────────────

def _visible_to_invisible(expr: str) -> str:
    """Convert a user-facing ``visible`` expression to Odoo's ``invisible``."""
    return f"not ({expr})"


def _process_field_kwargs(attrs: dict[str, str], kwargs: dict) -> None:
    """Process common keyword arguments for ``<field>`` elements."""
    for k, v in kwargs.items():
        if k == 'nolabel':
            attrs['nolabel'] = '1' if v else '0'
        elif k == 'visible':
            attrs['invisible'] = _visible_to_invisible(str(v))
        elif k == 'invisible':
            attrs['invisible'] = str(v)
        elif k.startswith('decoration_'):
            # decoration_danger → decoration-danger
            attrs[k.replace('_', '-', 1)] = v
        elif isinstance(v, bool):
            attrs[k] = '1' if v else '0'
        elif isinstance(v, (dict, list)):
            attrs[k] = str(v)
        else:
            attrs[k] = str(v)


def _flatten_nodes(items) -> list[Node]:
    """Flatten a mix of Nodes and lists of Nodes into a single list."""
    flat: list[Node] = []
    for item in items:
        if isinstance(item, list):
            flat.extend(item)
        elif isinstance(item, Node):
            flat.append(item)
    return flat


# ─── List View ───────────────────────────────────────────────────────

class ListViewBuilder:
    """Builder for ``<list>`` views.  Passed as ``v`` to ``@view.list`` functions.

    In **extend mode** (inherited views), ``header_button()`` auto-wraps
    in an xpath targeting ``//header``, and ``after()``/``before()``/
    ``inside()`` generate ``<xpath>`` operations.
    """

    def __init__(self, extend_mode: bool = False):
        self._extend_mode = extend_mode
        self._header: list[Node] = []
        self._fields: list[Node] = []
        self._stack: list[Node] = []

    @property
    def _target(self) -> list[Node]:
        """Current insertion target (top of stack or field list)."""
        return self._stack[-1].children if self._stack else self._fields

    # -- Header buttons --

    def header_button(self, method: str, string: str, *,
                      style: str | None = None, **kwargs):
        """Add a button to the list header bar.

        In extend mode, auto-wrapped in an xpath targeting ``//header``.
        """
        attrs = {'name': method, 'type': 'object', 'string': string}
        if style:
            attrs['class'] = f'btn-{style}'
        for k, v in kwargs.items():
            attrs[k] = str(v)
        btn_node = Node('button', attrs)

        if self._extend_mode:
            xpath = Node('_xpath_inside', {'target': 'header'})
            xpath.children.append(btn_node)
            self._target.append(xpath)
        else:
            self._header.append(btn_node)

    # -- Columns --

    def column(self, field_name: str, string: str | None = None, **kwargs):
        """Add a column (``<field>``) to the list."""
        attrs = {'name': field_name}
        if string:
            attrs['string'] = string
        _process_field_kwargs(attrs, kwargs)
        self._fields.append(Node('field', attrs))

    def badge(self, field_name: str, string: str | None = None, **kwargs):
        """Add a badge column.  Keyword args map decoration levels to values.

        Example::

            v.badge('state', 'Status', success='done', danger='error')
        """
        attrs = {'name': field_name, 'widget': 'badge'}
        if string:
            attrs['string'] = string
        for level in ('success', 'warning', 'danger', 'info', 'muted'):
            val = kwargs.pop(level, None)
            if val is not None:
                attrs[f'decoration-{level}'] = f"{field_name} == '{val}'"
        _process_field_kwargs(attrs, kwargs)
        self._fields.append(Node('field', attrs))

    # -- Inheritance (extend mode) --

    def make_field(self, field_name: str, string: str | None = None, **kwargs) -> Node:
        """Create a ``<field>`` node *without* appending it.

        Use with ``after()``/``before()`` for positioned insertion::

            v.after('name', v.make_field('custom', 'Custom'))
        """
        attrs = {'name': field_name}
        if string:
            attrs['string'] = string
        _process_field_kwargs(attrs, kwargs)
        return Node('field', attrs)

    def after(self, field_name: str, *nodes_or_lists):
        """Position nodes after a field (inherited views).

        Example::

            v.after('name', v.make_field('custom', 'Custom'))
        """
        flat = _flatten_nodes(nodes_or_lists)
        self._target.append(
            Node('_xpath_after', {'target': field_name}, children=flat)
        )

    def before(self, field_name: str, *nodes_or_lists):
        """Position nodes before a field (inherited views)."""
        flat = _flatten_nodes(nodes_or_lists)
        self._target.append(
            Node('_xpath_before', {'target': field_name}, children=flat)
        )

    @contextmanager
    def inside(self, xpath_target: str):
        """Place content inside an existing element (inherited views).

        Example::

            with v.inside('header'):
                v.header_button('action_do', 'Do It')
        """
        node = Node('_xpath_inside', {'target': xpath_target})
        self._target.append(node)
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    # -- Build --

    def build_children(self) -> list[Node]:
        """Return the complete list of child nodes for the ``<list>`` element."""
        children: list[Node] = []
        if self._header:
            children.append(Node('header', children=list(self._header)))
        children.extend(self._fields)
        return children


# ─── Form View ───────────────────────────────────────────────────────

class FormViewBuilder:
    """Builder for ``<form>`` views.  Passed as ``v`` to ``@view.form`` functions.

    In **extend mode** (inherited views):

    - ``header()`` delegates to ``inside('header')``
    - ``tab()`` wraps the page in an xpath targeting ``//notebook``
    - ``inside()``, ``after()``, ``before()`` generate ``<xpath>`` operations
    """

    def __init__(self, extend_mode: bool = False):
        self._extend_mode = extend_mode
        self._stack: list[Node] = []
        self._root_children: list[Node] = []

    @property
    def _target(self) -> list[Node]:
        """Current insertion target (top of stack or root)."""
        return self._stack[-1].children if self._stack else self._root_children

    # ── Fields ──

    def field(self, name: str, string: str | None = None, **kwargs):
        """Add a ``<field>`` element."""
        attrs = {'name': name}
        if string:
            attrs['string'] = string
        _process_field_kwargs(attrs, kwargs)
        self._target.append(Node('field', attrs))

    def badge(self, field_name: str, string: str | None = None, **kwargs):
        """Add a badge field."""
        attrs = {'name': field_name, 'widget': 'badge'}
        if string:
            attrs['string'] = string
        for level in ('success', 'warning', 'danger', 'info', 'muted'):
            val = kwargs.pop(level, None)
            if val is not None:
                attrs[f'decoration-{level}'] = f"{field_name} == '{val}'"
        _process_field_kwargs(attrs, kwargs)
        self._target.append(Node('field', attrs))

    def hidden(self, *names: str) -> list[Node]:
        """Create invisible field nodes.  Returns a list for use with ``.after()``."""
        return [Node('field', {'name': n, 'invisible': '1'}) for n in names]

    def make_field(self, name: str, string: str | None = None, **kwargs) -> Node:
        """Create a ``<field>`` node *without* appending it.

        Use with ``after()``/``before()`` for positioned insertion.
        """
        attrs = {'name': name}
        if string:
            attrs['string'] = string
        _process_field_kwargs(attrs, kwargs)
        return Node('field', attrs)

    # ── Buttons ──

    def button(self, method: str, string: str, *,
               style: str | None = None,
               visible: str | None = None,
               confirm: str | None = None,
               btn_type: str = 'object', **kwargs):
        """Add a ``<button>`` element."""
        attrs = {'name': method, 'type': btn_type, 'string': string}
        if style:
            attrs['class'] = f'btn-{style}'
        if visible:
            attrs['invisible'] = _visible_to_invisible(visible)
        if confirm:
            attrs['confirm'] = confirm
        for k, v in kwargs.items():
            attrs[k] = str(v)
        self._target.append(Node('button', attrs))

    def stat_button(self, method: str, string: str, *,
                    icon: str | None = None,
                    visible: str | None = None):
        """Add an ``oe_stat_button``."""
        attrs = {'name': method, 'type': 'object', 'class': 'oe_stat_button'}
        if icon:
            attrs['icon'] = icon
        if visible:
            attrs['invisible'] = _visible_to_invisible(visible)
        text_node = Node('span', {'class': 'o_stat_text'}, text=string)
        self._target.append(Node('button', attrs, children=[text_node]))

    # ── Containers (context managers) ──

    @contextmanager
    def header(self):
        """``<header>`` section — status bar and action buttons.

        In extend mode, delegates to ``inside('header')`` to generate
        the correct ``<xpath>`` wrapper.
        """
        if self._extend_mode:
            with self.inside('header'):
                yield
            return

        node = Node('header')
        self._target.append(node)
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    @contextmanager
    def sheet(self):
        """``<sheet>`` wrapper."""
        node = Node('sheet')
        self._target.append(node)
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    @contextmanager
    def group(self, string: str | None = None, **kwargs):
        """``<group>`` container.  Supports ``visible``, ``col``, ``colspan``."""
        attrs: dict[str, str] = {}
        if string:
            attrs['string'] = string
        if 'visible' in kwargs:
            attrs['invisible'] = _visible_to_invisible(kwargs.pop('visible'))
        for k in ('col', 'colspan'):
            if k in kwargs:
                attrs[k] = str(kwargs.pop(k))
        node = Node('group', attrs)
        self._target.append(node)
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    @contextmanager
    def tab(self, string: str, **kwargs):
        """``<page>`` inside a ``<notebook>``.

        In **standalone** mode, consecutive tabs share one ``<notebook>``.
        In **extend** mode, each tab generates an ``<xpath>`` targeting
        ``//notebook`` with ``position="inside"``.
        """
        page_attrs: dict[str, str] = {'string': string}
        if 'name' in kwargs:
            page_attrs['name'] = kwargs.pop('name')
        if 'visible' in kwargs:
            page_attrs['invisible'] = _visible_to_invisible(kwargs.pop('visible'))

        page = Node('page', page_attrs)

        if self._extend_mode:
            # Wrap in xpath targeting the parent view's notebook
            xpath = Node('_xpath_inside', {'target': 'notebook'})
            xpath.children.append(page)
            self._target.append(xpath)
        else:
            target = self._target
            # Re-use the last notebook if it's the most recent child
            if target and target[-1].tag == 'notebook':
                notebook = target[-1]
            else:
                notebook = Node('notebook')
                target.append(notebook)
            notebook.children.append(page)

        self._stack.append(page)
        try:
            yield
        finally:
            self._stack.pop()

    # ── Inheritance ──

    @contextmanager
    def inside(self, xpath_target: str):
        """Place content inside an existing element (inherited views).

        ``target`` is converted to an XPath expression:

        - ``'header'`` → ``//header``
        - ``'div[@name="button_box"]'`` → ``//div[@name="button_box"]``
        - ``'//custom/path'`` → used as-is
        """
        node = Node('_xpath_inside', {'target': xpath_target})
        self._target.append(node)
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    def after(self, field_name: str, *nodes_or_lists):
        """Position nodes after an existing field (inherited views).

        Example::

            v.after('partner_id',
                    v.hidden('has_products', 'order_id'))
        """
        flat = _flatten_nodes(nodes_or_lists)
        wrapper = Node('_xpath_after', {'target': field_name}, children=flat)
        self._target.append(wrapper)

    def before(self, field_name: str, *nodes_or_lists):
        """Position nodes before an existing field (inherited views)."""
        flat = _flatten_nodes(nodes_or_lists)
        wrapper = Node('_xpath_before', {'target': field_name}, children=flat)
        self._target.append(wrapper)

    # ── Build ──

    def build_children(self) -> list[Node]:
        """Return the root-level child nodes."""
        return list(self._root_children)


# ─── Action ──────────────────────────────────────────────────────────

class ActionBuilder:
    """Builder for window actions.  Passed as ``a`` to ``@action.window`` functions."""

    def __init__(self):
        self._views: list[dict] = []
        self._search_fields: list[dict] = []
        self._filters: list[dict] = []

    def view_list(self, view_id: str):
        """Reference a specific list view."""
        self._views.append({'type': 'list', 'id': view_id})

    def view_form(self, view_id: str):
        """Reference a specific form view."""
        self._views.append({'type': 'form', 'id': view_id})

    def search_field(self, name: str, **kwargs):
        """Add a searchable field to the search view.

        Example::

            a.search_field('name')
            a.search_field('partner_id')
        """
        self._search_fields.append({'name': name, **kwargs})

    def search_separator(self):
        """Add a ``<separator/>`` between search fields and filters."""
        self._search_fields.append({'_separator': True})

    def search_filter(self, name: str, string: str, *, domain=None):
        """Define a search filter for the action's search view."""
        self._filters.append({
            'name': name,
            'string': string,
            'domain': domain or [],
        })

    @property
    def view_mode(self) -> str:
        """Derive view_mode from referenced views."""
        if self._views:
            return ','.join(v['type'] for v in self._views)
        return 'list,form'


# ─── Settings ────────────────────────────────────────────────────────

class SettingsBuilder:
    """Builder for ``res.config.settings`` pages.

    Passed as ``s`` to ``@settings.page`` functions.  Generates the
    structured ``<app>/<block>/<setting>`` layout with correct
    CSS classes for the Odoo settings UI.

    Example::

        @settings.page(id='my_settings', module='my_mod', string='My App')
        def my_settings(s):
            with s.block('Connection'):
                with s.setting('API Key', help='Enter your API key.'):
                    s.field('api_key', password=True)
    """

    def __init__(self):
        self._app_children: list[Node] = []
        self._stack: list[Node] = []

    @property
    def _target(self) -> list[Node]:
        """Current insertion target."""
        return self._stack[-1].children if self._stack else self._app_children

    # ── Containers ──

    @contextmanager
    def block(self, title: str):
        """``<block title="...">`` — groups related settings."""
        node = Node('block', {'title': title})
        self._target.append(node)
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    @contextmanager
    def setting(self, string: str, *, help: str = ''):
        """``<setting string="..." help="...">`` — single setting entry.

        Inside this context, use ``field()``, ``checkbox()``, or
        ``button()`` to define the setting's content.
        """
        attrs: dict[str, str] = {'string': string}
        if help:
            attrs['help'] = help
        node = Node('setting', attrs)
        self._target.append(node)
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    # ── Fields ──

    def field(self, name: str, *,
              widget: str | None = None,
              readonly: bool = False,
              password: bool = False,
              placeholder: str | None = None,
              visible: str | None = None,
              suffix: str | None = None,
              **kwargs):
        """Add a labeled field row.

        Generates the standard Odoo settings row pattern::

            <div class="row mt16">
                <label for="name" class="col-lg-3 o_light_label"/>
                <field name="name" class="col-lg-9"/>
            </div>

        Parameters
        ----------
        visible : str, optional
            Wraps the field in ``<div invisible="not (expr)">``.
        suffix : str, optional
            Adds a text span after the field (e.g., "hours between syncs").
            Shrinks the field column to ``col-lg-2``.
        """
        if visible:
            # Conditional field — wrapped in visibility div, outside content-group
            wrapper = Node('div', {'invisible': f'not {visible}'})
            row = self._make_field_row(name, 'mt8',
                                       widget=widget, readonly=readonly,
                                       password=password, placeholder=placeholder,
                                       suffix=suffix, **kwargs)
            wrapper.children.append(row)
            self._target.append(wrapper)
        else:
            # Standard field — inside content-group
            cg = self._get_content_group()
            mt = 'mt16' if len(cg.children) == 0 else 'mt8'
            row = self._make_field_row(name, mt,
                                       widget=widget, readonly=readonly,
                                       password=password, placeholder=placeholder,
                                       suffix=suffix, **kwargs)
            cg.children.append(row)

    def checkbox(self, name: str):
        """Add a checkbox toggle (field + label inline).

        Generates::

            <div class="mt8">
                <field name="..."/>
                <label for="..."/>
            </div>
        """
        div = Node('div', {'class': 'mt8'})
        div.children.append(Node('field', {'name': name}))
        div.children.append(Node('label', {'for': name}))
        self._target.append(div)

    def button(self, method: str, string: str, *,
               style: str | None = None,
               icon: str | None = None, **kwargs):
        """Add a button.

        If inside a content-group (after ``field()`` calls), adds the
        button in a labeled-row layout.  Otherwise, adds it directly.
        """
        btn_attrs: dict[str, str] = {
            'name': method, 'type': 'object', 'string': string,
        }
        if style:
            btn_attrs['class'] = f'btn-{style}'
        if icon:
            btn_attrs['icon'] = icon
        for k, v in kwargs.items():
            btn_attrs[k] = str(v)
        btn = Node('button', btn_attrs)

        # Check if there's a content-group in the current target
        has_cg = any(
            c.tag == 'div' and c.attrs.get('class') == 'content-group'
            for c in self._target
        )

        if has_cg:
            # Button row inside content-group (empty label + button cell)
            cg = self._get_content_group()
            mt = 'mt16' if len(cg.children) == 0 else 'mt8'
            row = Node('div', {'class': f'row {mt}'})
            row.children.append(Node('div', {'class': 'col-lg-3'}))
            cell = Node('div', {'class': 'col-lg-9'})
            cell.children.append(btn)
            row.children.append(cell)
            cg.children.append(row)
        else:
            # Standalone button div
            div = Node('div', {'class': 'mt8'})
            div.children.append(btn)
            self._target.append(div)

    # ── Internal helpers ──

    def _get_content_group(self) -> Node:
        """Get or create the ``<div class="content-group">`` in the current setting."""
        for child in self._target:
            if child.tag == 'div' and child.attrs.get('class') == 'content-group':
                return child
        cg = Node('div', {'class': 'content-group'})
        self._target.append(cg)
        return cg

    def _make_field_row(self, name: str, mt: str, *,
                        widget: str | None = None,
                        readonly: bool = False,
                        password: bool = False,
                        placeholder: str | None = None,
                        suffix: str | None = None,
                        **kwargs) -> Node:
        """Build a ``<div class="row mt...">`` with label + field."""
        row = Node('div', {'class': f'row {mt}'})

        # Label column
        row.children.append(Node('label', {
            'for': name, 'class': 'col-lg-3 o_light_label',
        }))

        # Field column
        field_attrs: dict[str, str] = {'name': name}
        field_attrs['class'] = 'col-lg-2' if suffix else 'col-lg-9'
        if widget:
            field_attrs['widget'] = widget
        if readonly:
            field_attrs['readonly'] = '1'
        if password:
            field_attrs['password'] = 'True'
        if placeholder:
            field_attrs['placeholder'] = placeholder
        for k, v in kwargs.items():
            if isinstance(v, bool):
                field_attrs[k] = '1' if v else '0'
            else:
                field_attrs[k] = str(v)
        row.children.append(Node('field', field_attrs))

        # Suffix text
        if suffix:
            row.children.append(Node('span', {
                'class': 'col-lg-7 text-muted',
            }, text=suffix))

        return row

    # ── Build ──

    def build(self, module_name: str, app_string: str) -> list[Node]:
        """Produce the node tree for ``emit_view``.

        Returns a list containing a single ``_xpath_inside`` node wrapping
        the ``<app>`` element with all blocks and settings.
        """
        app = Node('app', {
            'data-string': app_string,
            'string': app_string,
            'name': module_name,
        }, children=self._app_children)

        wrapper = Node('_xpath_inside', {'target': 'form'})
        wrapper.children.append(app)
        return [wrapper]
