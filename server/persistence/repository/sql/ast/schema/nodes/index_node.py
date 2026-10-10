
from dataclasses import dataclass
from typing import override

from ..schema_visitor import SchemaVisitor
from .column_node import ColumnNode
from .visitable import Visitable


@dataclass
class IndexNode(Visitable):
    name: str
    columns: list[ColumnNode]

    @override
    def accept(self, visitor: SchemaVisitor) -> None:
        visitor.visit_index(self)
