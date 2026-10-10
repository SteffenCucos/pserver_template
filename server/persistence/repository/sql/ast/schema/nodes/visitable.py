
from abc import ABC, abstractmethod

from ..schema_visitor import SchemaVisitor


class Visitable(ABC):

    @abstractmethod
    def accept(self, visitor: SchemaVisitor) -> None:
        pass
