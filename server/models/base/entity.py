
from dataclasses import Field as DataclassField
from dataclasses import dataclass, fields
from datetime import datetime as Datetime
from typing import Any, ClassVar, Iterable

from persistence.models import INDEX, PRIMARY_KEY, field
from persistence.repository.sql.schema.types import (
    CheckConstraint,
    ForeignKey,
    Index,
    PrimaryKey,
    UniqueConstraint,
)
from typing_extensions import dataclass_transform

from .id import Id, create_id


@dataclass_transform(field_specifiers=(field,))
@dataclass(kw_only=True)
class IdEntity:
    id: Id = field(INDEX | PRIMARY_KEY, init=False)
    created_date: Datetime = field(init=False)
    updated_date: Datetime = field(init=False)

    table_name: ClassVar[str]
    primary_key: ClassVar[PrimaryKey]
    unique_constraints: ClassVar[list[UniqueConstraint]]
    indexes: ClassVar[list[Index]]
    check_constraints: ClassVar[list[CheckConstraint]]
    foreign_keys: ClassVar[list[ForeignKey]]


    def set_created_date(self) -> None:
        self.created_date = Datetime.now()

    def set_updated_date(self) -> None:
        self.updated_date = Datetime.now()

    @classmethod
    def iterate_field_metadata(cls: type['IdEntity']) -> Iterable[DataclassField[Any]]:
        """
        Returns a dictionary of field names and their values for the entity.
        """

        for _field in fields(cls):
            yield _field


def Entity(_id_source: str | None = None) -> type[IdEntity]:
    """
    Base Entity class that handles base fields and custom Id logic
    """
    @dataclass
    class WiredIdEntity(IdEntity):
        def __post_init__(self) -> None:
            if _id_source:
                self.id = Id(str(getattr(self, _id_source)))
            else:
                self.id = create_id()

            if not hasattr(self, "created_date"):
                self.set_created_date()

            if not hasattr(self, "updated_date"):
                self.set_updated_date()

    return WiredIdEntity
