
from abc import abstractmethod
from typing import override

from .nodes.table_node import TableNode
from .schema_visitor import SchemaVisitor


class SchemaGenerator(SchemaVisitor[TableNode, tuple[str, str]]):

    @abstractmethod
    def generate_create_sql(self) -> str:
        pass

    @abstractmethod
    def generate_update_sql(self) -> str:
        pass

    @override
    @classmethod
    def rewrite(cls, visitable: TableNode) -> tuple[str, str]:
        visitor = cls()
        visitable.accept(visitor)
        return visitor.generate_create_sql(), visitor.generate_update_sql()
