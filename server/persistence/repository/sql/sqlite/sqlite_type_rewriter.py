
from typing import override

from ..ast.schema.data_types import DataType
from ..ast.schema.nodes.column_node import ColumnNode
from ..ast.schema.table_rewriter import TableRewriter


class SqliteTypeRewriter(TableRewriter):

    @override
    def visit_column(self, column: ColumnNode) -> None:
        match column.type:
            case DataType.DOUBLE_PRECISION:
                column.type = "REAL"
            case DataType.INTEGER | DataType.BOOLEAN:
                column.type = DataType.INTEGER
            case _:
                column.type = DataType.TEXT

        super().visit_column(column)
