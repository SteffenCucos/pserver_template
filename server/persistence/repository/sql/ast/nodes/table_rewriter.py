
from typing import override

from ..visitor import Visitor
from .check_constraint_node import CheckConstraintNode
from .column_node import ColumnNode
from .foreign_key_node import ForeignKeyNode
from .index_node import IndexNode
from .primary_key_node import PrimaryKeyNode
from .table_node import TableNode
from .unique_constraint_node import UniqueCheckConstraintNode


class TableRewriter(Visitor):
    def __init__(self) -> None:
        super().__init__()
        self._table: TableNode | None = None
        self._columns: list[ColumnNode] = []
        self._primary_key: PrimaryKeyNode | None = None
        self._foreign_keys: list[ForeignKeyNode] = []
        self._unique_constraints: list[UniqueCheckConstraintNode] = []
        self._check_constraints: list[CheckConstraintNode] = []
        self._indexes: list[IndexNode] = []

    @override
    def visit_table(self, table: TableNode) -> None:
        self._table = table

    @override
    def visit_column(self, column: ColumnNode) -> None:
        self._columns.append(column)

    @override
    def visit_primary_key(self, primary_key: PrimaryKeyNode) -> None:
        self._primary_key = primary_key

    @override
    def visit_unique_constraint(self, unique_constraint: UniqueCheckConstraintNode) -> None:
        self._unique_constraints.append(unique_constraint)

    @override
    def visit_foreign_key(self, foreign_key: ForeignKeyNode) -> None:
        self._foreign_keys.append(foreign_key)

    @override
    def visit_check_constraint(self, constraint: CheckConstraintNode) -> None:
        self._check_constraints.append(constraint)

    @override
    def visit_index(self, index: IndexNode) -> None:
        self._indexes.append(index)

    @classmethod
    def rewrite(cls, table: TableNode) -> TableNode:
        rewriter = cls()
        table.accept(rewriter)
        new_table = TableNode(
            name=table.name,
            columns=rewriter._columns,
            primary_key=rewriter._primary_key,
            foreign_keys=rewriter._foreign_keys if rewriter._foreign_keys else None,
            unique_constraints=rewriter._unique_constraints if rewriter._unique_constraints else None,
            check_constraints=rewriter._check_constraints if rewriter._check_constraints else None,
            indexes=rewriter._indexes if rewriter._indexes else None,
        )
        return new_table
