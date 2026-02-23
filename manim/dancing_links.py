"""Minimal dancing-links (DLX) pointer operations.

This module focuses on the list operations themselves, not animation.

Core idea
- A node has left/right neighbors in a circular doubly linked list.
- Removing a node bypasses it.
- Restoring a node reconnects it using stored neighbors.

Pointer rules
- remove(x): x.left.right = x.right; x.right.left = x.left
- restore(x): x.left.right = x;       x.right.left = x
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class Node:
    """One node in a circular doubly linked list."""

    name: str
    left: "Node" | None = None
    right: "Node" | None = None

    def __post_init__(self) -> None:
        # Standalone nodes point to themselves, forming a 1-node ring.
        if self.left is None:
            self.left = self
        if self.right is None:
            self.right = self


def insert_after(anchor: Node, node: Node) -> None:
    """Insert ``node`` immediately to the right of ``anchor``."""
    right = anchor.right
    assert right is not None

    node.left = anchor
    node.right = right
    anchor.right = node
    right.left = node


def remove(node: Node) -> None:
    """Detach ``node`` from its neighbors, keeping node pointers intact."""
    left = node.left
    right = node.right
    assert left is not None
    assert right is not None

    left.right = right
    right.left = left


def restore(node: Node) -> None:
    """Undo ``remove(node)`` using the node's stored left/right pointers."""
    left = node.left
    right = node.right
    assert left is not None
    assert right is not None

    left.right = node
    right.left = node


def ring_values(head: Node) -> list[str]:
    """Return node names walking right from ``head`` until it loops."""
    values = [head.name]
    cur = head.right
    while cur is not None and cur is not head:
        values.append(cur.name)
        cur = cur.right
    return values


def build_ring(names: Iterable[str]) -> Node:
    """Build a circular doubly linked list and return the head node."""
    names = list(names)
    if not names:
        raise ValueError("names must contain at least one item")

    head = Node(names[0])
    for name in names[1:]:
        assert head.left is not None
        insert_after(head.left, Node(name))
    return head


def _find_by_name(head: Node, target: str) -> Node:
    cur = head
    while True:
        if cur.name == target:
            return cur
        cur = cur.right
        if cur is None or cur is head:
            break
    raise KeyError(f"node {target!r} not found")


def demo() -> None:
    """Small terminal demo matching the animation narrative."""
    head = build_ring(["H", "1", "2", "3", "4"])
    print("start       ", ring_values(head))

    n3 = _find_by_name(head, "3")
    remove(n3)
    print("remove(3)   ", ring_values(head))

    n2 = _find_by_name(head, "2")
    remove(n2)
    print("remove(2)   ", ring_values(head))

    restore(n2)
    print("restore(2)  ", ring_values(head))

    restore(n3)
    print("restore(3)  ", ring_values(head))


if __name__ == "__main__":
    demo()
