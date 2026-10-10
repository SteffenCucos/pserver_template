
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PermissionNode:
    children: dict[str, "PermissionNode"] = field(default_factory=dict)
    wildcard: "PermissionNode | None" = None
    deep_wildcard: bool = False
    allow: bool = False


class PermissionTree:
    def __init__(self) -> None:
        self.root = PermissionNode()

    def add(self, permission: str) -> None:
        parts = self._split(permission)
        node = self.root

        for part in parts:
            if part == "**":
                node.deep_wildcard = True
                node.allow = True
                return

            if part == "*" or not part.replace("_", "").replace("-", "").isalnum():
                if node.wildcard is None:
                    node.wildcard = PermissionNode()
                node = node.wildcard
            else:
                node = node.children.setdefault(part, PermissionNode())

        node.allow = True

    def allows(self, required: str) -> bool:
        return self._allows(self.root, self._split(required), 0)

    def _allows(self, node: PermissionNode, parts: list[str], index: int) -> bool:
        if node.deep_wildcard:
            return True

        if index == len(parts):
            return node.allow

        part = parts[index]
        exact_child = node.children.get(part)
        if exact_child and self._allows(exact_child, parts, index + 1):
            return True

        if node.wildcard and self._allows(node.wildcard, parts, index + 1):
            return True

        return False

    @staticmethod
    def _split(value: str) -> list[str]:
        return [part for part in value.strip("/").split("/") if part]
