
from typing import override

from ..ast.schema.data_types import DataType
from ..ast.schema.nodes.column_node import ColumnNode
from ..ast.schema.table_rewriter import TableRewriter


class PostgresTypeRewriter(TableRewriter):

    @override
    def visit_column(self, column: ColumnNode) -> None:
        match column.type:
            case DataType.JSON:
                column.type = "JSONB" # Postgres supports an optimized binary JSON format.
            case _:
                pass

        super().visit_column(column)
