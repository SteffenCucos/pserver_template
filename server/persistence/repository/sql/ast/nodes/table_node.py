
from dataclasses import dataclass
from typing import override

from ..visitable import Visitable
from ..visitor import Visitor
from .column_node import ColumnNode
from .unique_constraint_node import UniqueCheckConstraintNode
from .foreign_key_node import ForeignKeyNode
from .primary_key_node import PrimaryKeyNode
from .check_constraint_node import CheckConstraintNode
from .index_node import IndexNode


@dataclass
class TableNode(Visitable):
    name: str
    columns: list[ColumnNode]
    primary_key: PrimaryKeyNode | None = None
    foreign_keys: list[ForeignKeyNode] | None = None
    unique_constraints: list[UniqueCheckConstraintNode] | None = None
    check_constraints: list[CheckConstraintNode] | None = None
    indexes: list[IndexNode] | None = None

    @override
    def accept(self, visitor: Visitor) -> None:
        visitor.visit_table(self)
        for column in self.columns:
            column.accept(visitor)
        if self.primary_key:
            self.primary_key.accept(visitor)
        if self.unique_constraints:
            for unique_constraint in self.unique_constraints:
                unique_constraint.accept(visitor)
        if self.foreign_keys:
            for foreign_key in self.foreign_keys:
                foreign_key.accept(visitor)
        if self.check_constraints:
            for check_constraint in self.check_constraints:
                check_constraint.accept(visitor)
        if self.indexes:
            for index in self.indexes:
                index.accept(visitor)

    @override
    def __hash__(self) -> int:
        return hash((self.name, tuple(self.columns), self.primary_key, tuple(self.foreign_keys) if self.foreign_keys else None, tuple(self.unique_constraints) if self.unique_constraints else None, tuple(self.check_constraints) if self.check_constraints else None, tuple(self.indexes) if self.indexes else None))

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TableNode):
            return False
        return (self.name, tuple(self.columns), self.primary_key, tuple(self.foreign_keys) if self.foreign_keys else None, tuple(self.unique_constraints) if self.unique_constraints else None, tuple(self.check_constraints) if self.check_constraints else None, tuple(self.indexes) if self.indexes else None) == (other.name, tuple(other.columns), other.primary_key, tuple(other.foreign_keys) if other.foreign_keys else None, tuple(other.unique_constraints) if other.unique_constraints else None, tuple(other.check_constraints) if other.check_constraints else None, tuple(other.indexes) if other.indexes else None)
