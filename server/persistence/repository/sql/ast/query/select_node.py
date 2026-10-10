
from dataclasses import dataclass

from ...postgres.postgres_visitor import TableNode


@dataclass 
class SelectNode():
    from_: object | None
    where_clauses: list | None
    group_bys: list | None
    order_bys: list | None
