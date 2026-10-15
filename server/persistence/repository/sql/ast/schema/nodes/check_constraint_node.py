
from dataclasses import dataclass
from typing import override

from ..schema_visitor import SchemaVisitor
from .visitable import Visitable


@dataclass
class CheckConstraintNode(Visitable):
    name: str
    constraint: str

    @override
    def accept(self, visitor: SchemaVisitor) -> None:
        visitor.visit_check_constraint(self)
