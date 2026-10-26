
from dataclasses import dataclass
from typing import Any, override

from ..schema_visitor import SchemaVisitor
from .schema_node import SchemaNode


@dataclass
class CheckConstraintNode(SchemaNode):
    name: str
    constraint: str

    @override
    def accept(self, visitor: SchemaVisitor[Any, Any]) -> None:
        visitor.visit_check_constraint(self)
