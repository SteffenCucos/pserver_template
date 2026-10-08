
from abc import ABC, abstractmethod

from .visitor import Visitor

class Visitable(ABC):

    @abstractmethod
    def accept(self, visitor: Visitor) -> None:
        pass