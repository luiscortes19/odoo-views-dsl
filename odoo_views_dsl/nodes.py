"""Internal tree representation for view structures."""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field


@dataclass
class Node:
    """A single element in the view tree.

    Maps 1:1 to an XML element when emitted. The emitter walks
    the Node tree to produce valid Odoo XML.
    """
    tag: str
    attrs: dict[str, str] = dc_field(default_factory=dict)
    children: list[Node] = dc_field(default_factory=list)
    text: str | None = None

    def add(self, child: Node) -> Node:
        """Append a child node. Returns the child for chaining."""
        self.children.append(child)
        return child
