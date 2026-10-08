
from dataclasses import dataclass
from typing import override

from ..visitable import Visitable
from ..visitor import Visitor

@dataclass
class CheckConstraintNode(Visitable):
    name: str
    constraint: str

    @override
    def accept(self, visitor: Visitor) -> None:
        visitor.visit_check_constraint(self)
