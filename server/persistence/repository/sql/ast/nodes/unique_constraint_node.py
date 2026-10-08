
from dataclasses import dataclass
from typing import override

from ..visitable import Visitable
from ..visitor import Visitor
from .column_node import ColumnNode


@dataclass
class UniqueCheckConstraintNode(Visitable):
    name: str
    columns: list[ColumnNode]

    @override
    def accept(self, visitor: Visitor) -> None:
        visitor.visit_unique_constraint(self)
