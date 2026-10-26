
from dataclasses import dataclass


@dataclass
class Index:
    name: str
    columns: list[str]


@dataclass
class ForeignKey:
    name: str
    source_columns: list[str]
    referenced_table: str
    referenced_columns: list[str]


@dataclass
class PrimaryKey:
    name: str
    columns: list[str]


@dataclass
class UniqueConstraint:
    name: str
    columns: list[str]


@dataclass
class CheckConstraint:
    name: str
    expression: str
