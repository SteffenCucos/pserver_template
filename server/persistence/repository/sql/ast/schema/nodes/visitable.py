
from abc import ABC, abstractmethod
from typing import Any

from ..schema_visitor import SchemaVisitor


class Visitable(ABC):

    @abstractmethod
    def accept(self, visitor: SchemaVisitor[Any, Any]) -> None:
        pass
