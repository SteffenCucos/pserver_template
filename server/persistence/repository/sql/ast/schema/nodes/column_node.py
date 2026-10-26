
from dataclasses import dataclass
from typing import Any, override

from ..data_types import DataType
from ..schema_visitor import SchemaVisitor
from .schema_node import SchemaNode


@dataclass
class ColumnNode(SchemaNode): 
    name: str
    type: type | DataType | str
    nullable: bool

    @override
    def accept(self, visitor: SchemaVisitor[Any, Any]) -> None:
        visitor.visit_column(self)

    @override
    def __hash__(self) -> int:
        return hash((self.name, self.type, self.nullable))

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ColumnNode):
            return False
        return (self.name, self.type, self.nullable) == (other.name, other.type, other.nullable)
