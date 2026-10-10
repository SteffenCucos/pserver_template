
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from ..schema_visitor import SchemaVisitor
from .column_node import ColumnNode
from .visitable import Visitable


# TableNode imports ForeignKeyNode, so this is only needed for type checking
if TYPE_CHECKING:
    from .table_node import TableNode


@dataclass
class ForeignKeyNode(Visitable):
    name: str
    columns: list[ColumnNode]
    references: tuple[TableNode, list[ColumnNode]]

    def __post_init__(self) -> None:
        table, references = self.references
        if not self.columns:
            raise ValueError("ForeignKeyNode must have at least one column")
        if not table:
            raise ValueError("ForeignKeyNode must reference a table")
        if not references:
            raise ValueError("ForeignKeyNode must have at least one reference")
        if len(self.columns) != len(references):
            raise ValueError("The number of columns and references must match")
        for column, reference in zip(self.columns, references):
            if column.type != reference.type:
                raise ValueError("Column and reference types must match")
            
    @override
    def accept(self, visitor: SchemaVisitor) -> None:
        visitor.visit_foreign_key(self)
