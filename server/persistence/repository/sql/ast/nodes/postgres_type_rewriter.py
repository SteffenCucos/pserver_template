
from typing import override

from ..data_types import DataType
from .column_node import ColumnNode
from .table_rewriter import TableRewriter


class PostgresTypeRewriter(TableRewriter):

    @override
    def visit_column(self, column: ColumnNode) -> None:
        match column.type:
            case DataType.JSON:
                column.type = "JSONB" # Postgres supports an optimized binary JSON format.
            case _:
                pass

        super().visit_column(column)
