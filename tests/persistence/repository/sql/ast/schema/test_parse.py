
from dataclasses import dataclass
from datetime import datetime
from typing import cast, override

import pytest

from server.auth.rbac.models import Permission, Role, RolePermission, UserRole
from server.models.base.entity import Entity, IdEntity
from server.models.base.id import Id
from server.persistence.models import (
    CHECK,
    FOREIGN_KEY,
    INDEX,
    NOT_NULLABLE,
    NULLABLE,
    PRIMARY_KEY,
    UNIQUE,
    field,
)
from server.persistence.repository.sql.ast.schema.data_types import DataType
from server.persistence.repository.sql.ast.schema.exceptions import (
    FieldParsingException,
    TableParsingException,
)
from server.persistence.repository.sql.ast.schema.nodes.column_node import ColumnNode
from server.persistence.repository.sql.ast.schema.nodes.foreign_key_node import ForeignKeyNode
from server.persistence.repository.sql.ast.schema.nodes.table_node import TableNode
from server.persistence.repository.sql.ast.schema.parse import parse_entities_to_tables
from server.users.user import User


@dataclass
class Parent(Entity()):  # type: ignore[misc]
    name: str = field(NOT_NULLABLE)

    @staticmethod
    def table_name() -> str:
        return "parents"


def parse(*entities: type[IdEntity]) -> list[TableNode]:
    return parse_entities_to_tables(list(entities))


def columns_by_name(table: TableNode) -> dict[str, ColumnNode]:
    return {column.name: column for column in table.columns}


def describe_foreign_key(foreign_key: ForeignKeyNode) -> tuple[str, list[str], str, list[str]]:
    table, columns = foreign_key.references
    return (
        foreign_key.name,
        [column.name for column in foreign_key.columns],
        table.name,
        [column.name for column in columns],
    )


@dataclass
class TypesEntity(Entity()):
    date_f: datetime
    float_f: float
    int_f: int
    str_f: str
    dict_f: dict
    list_f: list
    bool_f: bool

    @override
    @staticmethod
    def table_name() -> str:
        return "types_entities"


@dataclass
class NullabilityEntity(Entity()):
    required: str
    nullable_by_metadata: str = field(NULLABLE)
    optional: str | None = None

    @override
    @staticmethod
    def table_name() -> str:
        return "nullability_entities"


@dataclass
class ForeignKeyEntity(Entity()):
    target_id: Id = field(FOREIGN_KEY("types_entities.id"))

    @override
    @staticmethod
    def table_name() -> str:
        return "foreign_key_entities"


@dataclass
class UniqueEntity(Entity()):
    value: str = field(UNIQUE)

    @override
    @staticmethod
    def table_name() -> str:
        return "unique_entities"


@dataclass
class CheckEntity(Entity()):
    value: int = field(CHECK("value > 0"))

    @override
    @staticmethod
    def table_name() -> str:
        return "check_entities"


@dataclass
class IndexEntity(Entity()):
    value: str = field(INDEX())

    @override
    @staticmethod
    def table_name() -> str:
        return "index_entities"


def test_parse_entities_to_tables_maps_fields_to_columns() -> None:
    table = parse(TypesEntity)[0]

    assert table.name == "types_entities"
    assert [(column.name, column.type) for column in table.columns] == [
        ("id", DataType.TEXT),
        ("created_date", DataType.TIMESTAMP),
        ("updated_date", DataType.TIMESTAMP),
        ("date_f", DataType.TIMESTAMP),
        ("float_f", DataType.DOUBLE_PRECISION),
        ("int_f", DataType.INTEGER),
        ("str_f", DataType.TEXT),
        ("dict_f", DataType.JSON),
        ("list_f", DataType.JSON),
        ("bool_f", DataType.BOOLEAN),
    ]


def test_parse_entities_to_tables_derives_nullability_from_type_and_metadata() -> None:
    columns = columns_by_name(parse(NullabilityEntity)[0])

    assert not columns["required"].nullable
    assert columns["nullable_by_metadata"].nullable
    assert columns["optional"].nullable


def test_parse_entities_to_tables_rejects_not_nullable_metadata_on_optional_types() -> None:
    @dataclass
    class ContradictoryNullability(Entity()):  # type: ignore[misc]
        value: str | None = field(NOT_NULLABLE)

        @staticmethod
        def table_name() -> str:
            return "contradictory_nullability"

    with pytest.raises(
        FieldParsingException,
        match="Field 'value' is marked as non nullable in its metadata but is typed as nullable",
    ):
        parse(ContradictoryNullability)


def test_parse_entities_to_tables_creates_primary_key_on_id() -> None:
    table = parse(TypesEntity)[0]

    assert table.primary_key is not None
    assert table.primary_key.name == "pk_types_entities_id"
    assert table.primary_key.columns == [columns_by_name(table)["id"]]


def test_parse_entities_to_tables_resolves_foreign_keys_to_nodes() -> None:
    target_table, foreign_key_table = parse(TypesEntity, ForeignKeyEntity)

    assert foreign_key_table.foreign_keys is not None
    [foreign_key] = foreign_key_table.foreign_keys
    assert foreign_key.name == "fk_foreign_key_entities_target_id"
    assert foreign_key.columns == [columns_by_name(foreign_key_table)["target_id"]]

    referenced_table, referenced_columns = foreign_key.references
    assert referenced_table is target_table
    assert len(referenced_columns) == 1
    assert referenced_columns[0] is columns_by_name(target_table)["id"]


def test_parse_entities_to_tables_creates_unique_constraints() -> None:
    table = parse(UniqueEntity)[0]

    assert table.unique_constraints is not None
    [unique_constraint] = table.unique_constraints
    assert unique_constraint.name == "uq_unique_entities_value"
    assert unique_constraint.columns == [columns_by_name(table)["value"]]


def test_parse_entities_to_tables_creates_check_constraints() -> None:
    table = parse(CheckEntity)[0]

    assert table.check_constraints is not None
    [check_constraint] = table.check_constraints
    assert check_constraint.name == "chk_check_entities_value"
    assert check_constraint.constraint == "value > 0"


def test_parse_entities_to_tables_creates_indexes() -> None:
    table = parse(IndexEntity)[0]

    assert table.indexes is not None
    [index] = table.indexes
    assert index.name == "idx_index_entities_value"
    assert index.columns == [columns_by_name(table)["value"]]


def test_parse_entities_to_tables_resolves_role_permission_relationships() -> None:
    tables = parse(Permission, Role, RolePermission, User, UserRole)
    tables_by_name = {table.name: table for table in tables}

    assert set(tables_by_name) == {"permissions", "roles", "role_permissions", "users", "user_roles"}

    role_permission_foreign_keys = tables_by_name["role_permissions"].foreign_keys or []
    assert [describe_foreign_key(fk) for fk in role_permission_foreign_keys] == [
        ("fk_role_permissions_role_id", ["role_id"], "roles", ["id"]),
        ("fk_role_permissions_permission_id", ["permission_id"], "permissions", ["id"]),
    ]

    user_role_foreign_keys = tables_by_name["user_roles"].foreign_keys or []
    assert [describe_foreign_key(fk) for fk in user_role_foreign_keys] == [
        ("fk_user_roles_user_id", ["user_id"], "users", ["id"]),
        ("fk_user_roles_role_id", ["role_id"], "roles", ["id"]),
    ]


def test_parse_entities_to_tables_rejects_multiple_primary_keys() -> None:
    @dataclass
    class TwoPrimaryKeys(Entity()):  # type: ignore[misc]
        other_id: Id = field(PRIMARY_KEY)

        @staticmethod
        def table_name() -> str:
            return "two_primary_keys"

    with pytest.raises(
        TableParsingException, match="Multiple primary keys defined for table 'two_primary_keys'"
    ):
        parse(TwoPrimaryKeys)


def test_parse_entities_to_tables_rejects_non_string_foreign_keys() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY(cast(str, 1)))

        @staticmethod
        def table_name() -> str:
            return "children"

    with pytest.raises(TableParsingException, match="Foreign key must be a string"):
        parse(Parent, Child)


def test_parse_entities_to_tables_rejects_malformed_foreign_keys() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("parents-id"))

        @staticmethod
        def table_name() -> str:
            return "children"

    with pytest.raises(TableParsingException, match="Foreign key must be a string"):
        parse(Parent, Child)


def test_parse_entities_to_tables_rejects_foreign_keys_to_unknown_tables() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("unknown_parents.id"))

        @staticmethod
        def table_name() -> str:
            return "children"

    with pytest.raises(TableParsingException, match="Foreign key table 'unknown_parents' not found"):
        parse(Parent, Child)


def test_parse_entities_to_tables_rejects_foreign_keys_to_unknown_fields() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("parents.unknown_id"))

        @staticmethod
        def table_name() -> str:
            return "children"

    with pytest.raises(TableParsingException, match="Foreign key field 'unknown_id' not found"):
        parse(Parent, Child)
