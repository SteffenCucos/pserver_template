
from dataclasses import dataclass


@dataclass 
class SelectNode():
    from_: object | None
    where_clauses: list[object] | None
    group_bys: list[object] | None
    order_bys: list[object] | None
