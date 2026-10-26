
from dataclasses import dataclass
from typing import Any, override

from ..schema_visitor import SchemaVisitor
from .column_node import ColumnNode
from .schema_node import SchemaNode


@dataclass
class UniqueCheckConstraintNode(SchemaNode):
    name: str
    columns: list[ColumnNode]

    @override
    def accept(self, visitor: SchemaVisitor[Any, Any]) -> None:
        visitor.visit_unique_constraint(self)
