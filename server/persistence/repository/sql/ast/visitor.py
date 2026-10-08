
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# Nodes import Visitor, so these are only needed for type checking
if TYPE_CHECKING:
    from .nodes.check_constraint_node import CheckConstraintNode
    from .nodes.column_node import ColumnNode
    from .nodes.foreign_key_node import ForeignKeyNode
    from .nodes.index_node import IndexNode
    from .nodes.primary_key_node import PrimaryKeyNode
    from .nodes.table_node import TableNode
    from .nodes.unique_constraint_node import UniqueCheckConstraintNode


class Visitor(ABC):
    
    @abstractmethod
    def visit_column(self, column: ColumnNode) -> None:
        pass

    @abstractmethod
    def visit_table(self, table: TableNode) -> None:
        pass

    @abstractmethod
    def visit_primary_key(self, primary_key: PrimaryKeyNode) -> None:
        pass

    @abstractmethod
    def visit_unique_constraint(self, unique_constraint: UniqueCheckConstraintNode) -> None:
        pass

    @abstractmethod
    def visit_foreign_key(self, foreign_key: ForeignKeyNode) -> None:
        pass

    @abstractmethod
    def visit_check_constraint(self, constraint: CheckConstraintNode) -> None:
        pass

    @abstractmethod
    def visit_index(self, index: IndexNode) -> None:
        pass
