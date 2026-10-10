
from dataclasses import dataclass
from typing import override

from ..schema_visitor import SchemaVisitor
from .column_node import ColumnNode
from .visitable import Visitable


@dataclass
class PrimaryKeyNode(Visitable):
    name: str
    columns: list[ColumnNode]

    @override
    def accept(self, visitor: SchemaVisitor) -> None:
        visitor.visit_primary_key(self)
