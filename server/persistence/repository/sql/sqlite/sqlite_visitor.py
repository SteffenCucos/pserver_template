
from typing import override

from ..ast.schema.nodes.check_constraint_node import CheckConstraintNode
from ..ast.schema.nodes.column_node import ColumnNode
from ..ast.schema.nodes.foreign_key_node import ForeignKeyNode
from ..ast.schema.nodes.index_node import IndexNode
from ..ast.schema.nodes.primary_key_node import PrimaryKeyNode
from ..ast.schema.nodes.table_node import TableNode
from ..ast.schema.nodes.unique_constraint_node import UniqueCheckConstraintNode
from ..ast.schema.schema_visitor import SchemaVisitor


class SqliteVisitor(SchemaVisitor):
    def __init__(self) -> None:
        self.columns: list[str] = []
        self.constraints: list[str] = []
        self.indexes: list[str] = []
        self.table: str | None = None

    @override
    def visit_column(self, column: ColumnNode) -> None:
        statement = f"{column.name} {column.type}"
        if not column.nullable:
            statement += " NOT NULL"
        statement += ",\n"
        self.columns.append(statement)

    @override
    def visit_table(self, table: TableNode) -> None:
        self.table = table.name

    @override
    def visit_primary_key(self, primary_key: PrimaryKeyNode) -> None:
        pk_name = primary_key.name
        pk_columns = [c.name for c in primary_key.columns]
        pk_statement = f"CONSTRAINT {pk_name} " if pk_name else ""
        pk_statement += f"PRIMARY KEY ({', '.join(pk_columns)})"
        self.constraints.append(pk_statement + ",\n")

    @override
    def visit_unique_constraint(self, unique_constraint: UniqueCheckConstraintNode) -> None:
        uc_name = unique_constraint.name
        uc_columns = [c.name for c in unique_constraint.columns]
        uc_statement = f"CONSTRAINT {uc_name} " if uc_name else ""
        self.constraints.append(
            f"{uc_statement}UNIQUE ({', '.join(uc_columns)}),\n"
        )
    
    @override
    def visit_foreign_key(self, foreign_key: ForeignKeyNode) -> None:
        fk_name = foreign_key.name
        fk_columns = [c.name for c in foreign_key.columns]
        ref_table, ref_columns = foreign_key.references
        ref_column_names = list(map(lambda c: c.name, ref_columns))
        ref_table_name = ref_table.name
        fk_statement = f"CONSTRAINT {fk_name} " if fk_name else ""
        self.constraints.append(
            f"{fk_statement}FOREIGN KEY ({', '.join(fk_columns)}) REFERENCES {ref_table_name} ({', '.join(ref_column_names)}),\n"
        )

    @override
    def visit_check_constraint(self, constraint: CheckConstraintNode) -> None:
        cc_name = constraint.name
        cc_statement = f"CONSTRAINT {cc_name} " if cc_name else ""
        cc_statement += f"CHECK ({constraint.constraint})"
        self.constraints.append(cc_statement + ",\n")

    @override
    def visit_index(self, index: IndexNode) -> None:
        idx_name = index.name
        idx_columns = [c.name for c in index.columns]
        idx_statement = f"CREATE INDEX {idx_name} ON {self.table} ({', '.join(idx_columns)});"
        self.indexes.append(idx_statement)

    def _create_table_sql(self) -> str:
        """
        Create table with columns and constraints. SQLite's ALTER TABLE can't add constraints, so they're declared inline.
        """
        sql_parts: list[str] = [f"CREATE TABLE {self.table} (\n"]
        sql_parts.extend(self.columns)
        sql_parts.extend(self.constraints)
        sql_parts[-1] = sql_parts[-1].rstrip(",\n") + "\n"
        sql_parts.append(");")
        return "".join(sql_parts)

    @staticmethod
    def rewrite(table: TableNode) -> list[str]:
        """
        Returns one statement per element (table first, then indexes), since sqlite3 executes one statement at a time.
        """
        visitor = SqliteVisitor()
        table.accept(visitor)
        return [visitor._create_table_sql(), *visitor.indexes]
