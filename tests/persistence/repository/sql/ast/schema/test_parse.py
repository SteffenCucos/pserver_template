
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, cast

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
from server.persistence.repository.sql.ast.schema.nodes.check_constraint_node import (
    CheckConstraintNode,
)
from server.persistence.repository.sql.ast.schema.nodes.column_node import ColumnNode
from server.persistence.repository.sql.ast.schema.nodes.foreign_key_node import ForeignKeyNode
from server.persistence.repository.sql.ast.schema.nodes.index_node import IndexNode
from server.persistence.repository.sql.ast.schema.nodes.primary_key_node import PrimaryKeyNode
from server.persistence.repository.sql.ast.schema.nodes.table_node import TableNode
from server.persistence.repository.sql.ast.schema.nodes.unique_constraint_node import (
    UniqueCheckConstraintNode,
)
from server.persistence.repository.sql.ast.schema.parse import parse_entities_to_tables
from server.persistence.repository.sql.schema.types import (
    CheckConstraint,
    ForeignKey,
    Index,
    PrimaryKey,
    UniqueConstraint,
)
from server.users.user import User


@dataclass
class Parent(Entity()):  # type: ignore[misc]
    name: str = field(NOT_NULLABLE)

    table_name: ClassVar[str] = "parents"


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


def describe_column_constraints(
    nodes: Sequence[PrimaryKeyNode | UniqueCheckConstraintNode | IndexNode] | None,
) -> list[tuple[str, list[str]]]:
    return [(node.name, [column.name for column in node.columns]) for node in nodes or []]


def describe_check_constraints(nodes: list[CheckConstraintNode] | None) -> list[tuple[str, str]]:
    return [(node.name, node.constraint) for node in nodes or []]


@dataclass
class TypesEntity(Entity()):
    date_f: datetime
    float_f: float
    int_f: int
    str_f: str
    dict_f: dict
    list_f: list
    bool_f: bool

    table_name: ClassVar[str] = "types_entities"


@dataclass
class NullabilityEntity(Entity()):
    required: str
    nullable_by_metadata: str = field(NULLABLE)
    optional: str | None = None

    table_name: ClassVar[str] = "nullability_entities"


@dataclass
class ForeignKeyEntity(Entity()):
    target_id: Id = field(FOREIGN_KEY("types_entities.id"))

    table_name: ClassVar[str] = "foreign_key_entities"


@dataclass
class UniqueEntity(Entity()):
    value: str = field(UNIQUE)

    table_name: ClassVar[str] = "unique_entities"


@dataclass
class CheckEntity(Entity()):
    value: int = field(CHECK("value > 0"))

    table_name: ClassVar[str] = "check_entities"


@dataclass
class IndexEntity(Entity()):
    value: str = field(INDEX)

    table_name: ClassVar[str] = "index_entities"


@dataclass
class CompositeParent(Entity()):
    code: str
    region: str

    table_name: ClassVar[str] = "composite_parents"


@dataclass
class TablePrimaryKeyEntity(Entity()):
    # Redeclared without PRIMARY_KEY so the table level primary key applies
    id: Id = field(init=False)
    code: str
    region: str

    table_name: ClassVar[str] = "table_primary_key_entities"
    primary_key: ClassVar[PrimaryKey] = PrimaryKey(
        "pk_table_primary_key_entities_code_region", ["code", "region"]
    )


@dataclass
class TableForeignKeyEntity(Entity()):
    parent_code: str
    parent_region: str
    owner_id: Id = field(FOREIGN_KEY("composite_parents.id"))

    table_name: ClassVar[str] = "table_foreign_key_entities"
    foreign_keys: ClassVar[list[ForeignKey]] = [
        ForeignKey(
            "fk_table_foreign_key_entities_parent",
            ["parent_code", "parent_region"],
            "composite_parents",
            ["code", "region"],
        ),
    ]


@dataclass
class ReorderedForeignKeyEntity(Entity()):
    parent_code: str
    parent_region: str

    table_name: ClassVar[str] = "reordered_foreign_key_entities"
    foreign_keys: ClassVar[list[ForeignKey]] = [
        # Referenced columns listed in the opposite order to CompositeParent's fields
        ForeignKey(
            "fk_reordered_foreign_key_entities_parent",
            ["parent_region", "parent_code"],
            "composite_parents",
            ["region", "code"],
        ),
    ]


@dataclass
class TableUniqueEntity(Entity()):
    first: str
    second: str
    third: str = field(UNIQUE)

    table_name: ClassVar[str] = "table_unique_entities"
    unique_constraints: ClassVar[list[UniqueConstraint]] = [
        UniqueConstraint("uq_table_unique_entities_first_second", ["first", "second"]),
    ]


@dataclass
class TableCheckEntity(Entity()):
    low: int
    high: int = field(CHECK("high > 0"))

    table_name: ClassVar[str] = "table_check_entities"
    check_constraints: ClassVar[list[CheckConstraint]] = [
        CheckConstraint("chk_table_check_entities_range", "low < high"),
    ]


@dataclass
class TableIndexEntity(Entity()):
    first: str
    second: str
    third: str = field(INDEX)

    table_name: ClassVar[str] = "table_index_entities"
    indexes: ClassVar[list[Index]] = [
        Index("idx_table_index_entities_first_second", ["first", "second"]),
    ]


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

        table_name: ClassVar[str] = "contradictory_nullability"

    with pytest.raises(
        FieldParsingException,
        match="Field 'value' is marked as non nullable in its metadata but is typed as nullable",
    ):
        parse(ContradictoryNullability)


def test_parse_entities_to_tables_rejects_missing_table_name() -> None:
    @dataclass
    class NoTableName(Entity()):  # type: ignore[misc]
        value: str

    with pytest.raises(
        TableParsingException, match="Entity 'NoTableName' must have a table_name attribute"
    ):
        parse(NoTableName)


def test_parse_entities_to_tables_rejects_empty_table_name() -> None:
    @dataclass
    class EmptyTableName(Entity()):  # type: ignore[misc]
        value: str

        table_name: ClassVar[str] = ""

    with pytest.raises(
        TableParsingException, match="Entity 'EmptyTableName' must have a table_name attribute"
    ):
        parse(EmptyTableName)


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


def test_parse_entities_to_tables_applies_role_permission_table_constraints() -> None:
    tables = parse(Permission, Role, RolePermission, User, UserRole)
    tables_by_name = {table.name: table for table in tables}

    assert describe_column_constraints(tables_by_name["permissions"].unique_constraints) == [
        ("uq_permission_key", ["key"]),
    ]
    assert describe_column_constraints(tables_by_name["role_permissions"].unique_constraints) == [
        ("uq_role_permission_role_id_permission_id", ["role_id", "permission_id"]),
    ]
    assert describe_column_constraints(tables_by_name["user_roles"].unique_constraints) == [
        ("uq_user_role_user_id_role_id", ["user_id", "role_id"]),
    ]


def test_parse_entities_to_tables_rejects_multiple_primary_keys() -> None:
    @dataclass
    class TwoPrimaryKeys(Entity()):  # type: ignore[misc]
        other_id: Id = field(PRIMARY_KEY)

        table_name: ClassVar[str] = "two_primary_keys"

    with pytest.raises(
        FieldParsingException,
        match="Multiple primary keys defined for table 'two_primary_keys': id, other_id",
    ):
        parse(TwoPrimaryKeys)


def test_parse_entities_to_tables_rejects_non_string_foreign_keys() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY(cast(str, 1)))

        table_name: ClassVar[str] = "children"

    with pytest.raises(TableParsingException, match="Foreign key must be a string"):
        parse(Parent, Child)


def test_parse_entities_to_tables_rejects_malformed_foreign_keys() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("parents-id"))

        table_name: ClassVar[str] = "children"

    with pytest.raises(TableParsingException, match="Foreign key must be a string"):
        parse(Parent, Child)


def test_parse_entities_to_tables_rejects_foreign_keys_to_unknown_tables() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("unknown_parents.id"))

        table_name: ClassVar[str] = "children"

    with pytest.raises(TableParsingException, match="Foreign key table 'unknown_parents' not found"):
        parse(Parent, Child)


def test_parse_entities_to_tables_rejects_foreign_keys_to_unknown_fields() -> None:
    @dataclass
    class Child(Entity()):  # type: ignore[misc]
        parent_id: Id = field(NOT_NULLABLE | FOREIGN_KEY("parents.unknown_id"))

        table_name: ClassVar[str] = "children"

    with pytest.raises(TableParsingException, match="Foreign key field 'unknown_id' not found"):
        parse(Parent, Child)


# Table level metadata

def test_parse_entities_to_tables_creates_table_primary_key() -> None:
    table = parse(TablePrimaryKeyEntity)[0]

    assert describe_column_constraints([table.primary_key] if table.primary_key else None) == [
        ("pk_table_primary_key_entities_code_region", ["code", "region"]),
    ]


def test_parse_entities_to_tables_rejects_table_and_column_primary_keys() -> None:
    @dataclass
    class ConflictingPrimaryKeys(Entity()):  # type: ignore[misc]
        code: str

        table_name: ClassVar[str] = "conflicting_primary_keys"
        primary_key: ClassVar[PrimaryKey] = PrimaryKey("pk_conflicting_primary_keys", ["code"])

    with pytest.raises(
        FieldParsingException,
        match="Conflicting primary key definitions for table 'conflicting_primary_keys'",
    ):
        parse(ConflictingPrimaryKeys)


def test_parse_entities_to_tables_rejects_table_primary_key_with_unknown_columns() -> None:
    @dataclass
    class UnknownPrimaryKeyColumn(Entity()):  # type: ignore[misc]
        id: Id = field(init=False)
        code: str

        table_name: ClassVar[str] = "unknown_primary_key_columns"
        primary_key: ClassVar[PrimaryKey] = PrimaryKey(
            "pk_unknown_primary_key_columns", ["code", "missing"]
        )

    with pytest.raises(
        TableParsingException,
        match=(
            "Constraint 'pk_unknown_primary_key_columns' references unknown columns "
            "in table 'unknown_primary_key_columns': missing"
        ),
    ):
        parse(UnknownPrimaryKeyColumn)


def test_parse_entities_to_tables_creates_table_foreign_keys_before_column_foreign_keys() -> None:
    parent_table, child_table = parse(CompositeParent, TableForeignKeyEntity)

    assert [describe_foreign_key(fk) for fk in child_table.foreign_keys or []] == [
        (
            "fk_table_foreign_key_entities_parent",
            ["parent_code", "parent_region"],
            "composite_parents",
            ["code", "region"],
        ),
        ("fk_table_foreign_key_entities_owner_id", ["owner_id"], "composite_parents", ["id"]),
    ]

    composite_foreign_key = (child_table.foreign_keys or [])[0]
    referenced_table, referenced_columns = composite_foreign_key.references
    assert referenced_table is parent_table
    parent_columns = columns_by_name(parent_table)
    assert referenced_columns[0] is parent_columns["code"]
    assert referenced_columns[1] is parent_columns["region"]


def test_parse_entities_to_tables_rejects_table_and_column_foreign_keys_on_same_column() -> None:
    @dataclass
    class DoubleForeignKey(Entity()):  # type: ignore[misc]
        parent_id: Id = field(FOREIGN_KEY("parents.id"))

        table_name: ClassVar[str] = "double_foreign_keys"
        foreign_keys: ClassVar[list[ForeignKey]] = [
            ForeignKey("fk_double_foreign_keys_parent", ["parent_id"], "parents", ["id"]),
        ]

    with pytest.raises(
        FieldParsingException,
        match="Conflicting foreign key definitions for table 'double_foreign_keys'.*'parent_id'",
    ):
        parse(Parent, DoubleForeignKey)


def test_parse_entities_to_tables_orders_table_foreign_key_references_as_declared() -> None:
    parent_table, child_table = parse(CompositeParent, ReorderedForeignKeyEntity)

    assert [describe_foreign_key(fk) for fk in child_table.foreign_keys or []] == [
        (
            "fk_reordered_foreign_key_entities_parent",
            ["parent_region", "parent_code"],
            "composite_parents",
            ["region", "code"],
        ),
    ]

    [foreign_key] = child_table.foreign_keys or []
    _, referenced_columns = foreign_key.references
    parent_columns = columns_by_name(parent_table)
    assert referenced_columns[0] is parent_columns["region"]
    assert referenced_columns[1] is parent_columns["code"]


def test_parse_entities_to_tables_rejects_table_foreign_key_with_unknown_columns() -> None:
    @dataclass
    class UnknownForeignKeyColumn(Entity()):  # type: ignore[misc]
        parent_code: str

        table_name: ClassVar[str] = "unknown_foreign_key_columns"
        foreign_keys: ClassVar[list[ForeignKey]] = [
            ForeignKey(
                "fk_unknown_foreign_key_columns_parent",
                ["parent_code", "parent_region"],
                "composite_parents",
                ["code", "region"],
            ),
        ]

    with pytest.raises(
        TableParsingException,
        match=(
            "Constraint 'fk_unknown_foreign_key_columns_parent' references unknown columns "
            "in table 'unknown_foreign_key_columns': parent_region"
        ),
    ):
        parse(CompositeParent, UnknownForeignKeyColumn)


def test_parse_entities_to_tables_rejects_table_foreign_keys_to_unknown_tables() -> None:
    @dataclass
    class UnknownForeignKeyTable(Entity()):  # type: ignore[misc]
        parent_id: Id

        table_name: ClassVar[str] = "unknown_foreign_key_tables"
        foreign_keys: ClassVar[list[ForeignKey]] = [
            ForeignKey("fk_unknown_foreign_key_tables_parent", ["parent_id"], "unknown_parents", ["id"]),
        ]

    with pytest.raises(
        TableParsingException,
        match=(
            "Foreign key table 'unknown_parents' not found for foreign key "
            "'fk_unknown_foreign_key_tables_parent' in table 'unknown_foreign_key_tables'"
        ),
    ):
        parse(UnknownForeignKeyTable)


def test_parse_entities_to_tables_rejects_table_foreign_keys_to_unknown_columns() -> None:
    @dataclass
    class UnknownReferencedColumn(Entity()):  # type: ignore[misc]
        parent_code: str
        parent_region: str

        table_name: ClassVar[str] = "unknown_referenced_columns"
        foreign_keys: ClassVar[list[ForeignKey]] = [
            ForeignKey(
                "fk_unknown_referenced_columns_parent",
                ["parent_code", "parent_region"],
                "composite_parents",
                ["code", "missing"],
            ),
        ]

    with pytest.raises(
        FieldParsingException,
        match=(
            "Referenced columns for foreign key 'fk_unknown_referenced_columns_parent' "
            "do not match the expected columns in table 'composite_parents'. Missing columns: missing"
        ),
    ):
        parse(CompositeParent, UnknownReferencedColumn)


def test_parse_entities_to_tables_rejects_table_foreign_keys_with_mismatched_column_counts() -> None:
    @dataclass
    class MismatchedForeignKey(Entity()):  # type: ignore[misc]
        parent_code: str
        parent_region: str

        table_name: ClassVar[str] = "mismatched_foreign_keys"
        foreign_keys: ClassVar[list[ForeignKey]] = [
            ForeignKey(
                "fk_mismatched_foreign_keys_parent",
                ["parent_code", "parent_region"],
                "composite_parents",
                ["code"],
            ),
        ]

    with pytest.raises(
        TableParsingException,
        match=(
            "Foreign key 'fk_mismatched_foreign_keys_parent' in table 'mismatched_foreign_keys' "
            "has 2 source columns but 1 referenced columns"
        ),
    ):
        parse(CompositeParent, MismatchedForeignKey)


def test_parse_entities_to_tables_creates_table_unique_constraints_before_column_ones() -> None:
    table = parse(TableUniqueEntity)[0]

    assert describe_column_constraints(table.unique_constraints) == [
        ("uq_table_unique_entities_first_second", ["first", "second"]),
        ("uq_table_unique_entities_third", ["third"]),
    ]


def test_parse_entities_to_tables_rejects_table_and_column_unique_on_same_column() -> None:
    @dataclass
    class DoubleUnique(Entity()):  # type: ignore[misc]
        value: str = field(UNIQUE)

        table_name: ClassVar[str] = "double_uniques"
        unique_constraints: ClassVar[list[UniqueConstraint]] = [
            UniqueConstraint("uq_double_uniques_value", ["value"]),
        ]

    with pytest.raises(TableParsingException, match="Overlapping single-column unique constraints"):
        parse(DoubleUnique)


def test_parse_entities_to_tables_rejects_table_unique_constraints_with_unknown_columns() -> None:
    @dataclass
    class UnknownUniqueColumn(Entity()):  # type: ignore[misc]
        first: str

        table_name: ClassVar[str] = "unknown_unique_columns"
        unique_constraints: ClassVar[list[UniqueConstraint]] = [
            UniqueConstraint("uq_unknown_unique_columns_first_second", ["first", "second"]),
        ]

    with pytest.raises(
        TableParsingException,
        match=(
            "Constraint 'uq_unknown_unique_columns_first_second' references unknown columns "
            "in table 'unknown_unique_columns': second"
        ),
    ):
        parse(UnknownUniqueColumn)


def test_parse_entities_to_tables_creates_column_check_constraints_before_table_ones() -> None:
    table = parse(TableCheckEntity)[0]

    assert describe_check_constraints(table.check_constraints) == [
        ("chk_table_check_entities_high", "high > 0"),
        ("chk_table_check_entities_range", "low < high"),
    ]


def test_parse_entities_to_tables_rejects_duplicate_table_and_column_checks() -> None:
    @dataclass
    class DoubleCheck(Entity()):  # type: ignore[misc]
        value: int = field(CHECK("value > 0"))

        table_name: ClassVar[str] = "double_checks"
        check_constraints: ClassVar[list[CheckConstraint]] = [
            CheckConstraint("chk_double_checks_positive", "value > 0"),
        ]

    with pytest.raises(
        TableParsingException,
        match="Duplicate check constraints found for columns: value in table 'double_checks'",
    ):
        parse(DoubleCheck)


def test_parse_entities_to_tables_creates_table_indexes_before_column_indexes() -> None:
    table = parse(TableIndexEntity)[0]

    assert describe_column_constraints(table.indexes) == [
        ("idx_table_index_entities_first_second", ["first", "second"]),
        ("idx_table_index_entities_third", ["third"]),
    ]


def test_parse_entities_to_tables_rejects_table_and_column_index_on_same_column() -> None:
    @dataclass
    class DoubleIndex(Entity()):  # type: ignore[misc]
        value: str = field(INDEX)

        table_name: ClassVar[str] = "double_indexes"
        indexes: ClassVar[list[Index]] = [Index("idx_double_indexes_value", ["value"])]

    with pytest.raises(
        TableParsingException,
        match="Duplicate single-column indexes found for columns: value in table 'double_indexes'",
    ):
        parse(DoubleIndex)


def test_parse_entities_to_tables_rejects_table_indexes_with_unknown_columns() -> None:
    @dataclass
    class UnknownIndexColumn(Entity()):  # type: ignore[misc]
        first: str

        table_name: ClassVar[str] = "unknown_index_columns"
        indexes: ClassVar[list[Index]] = [
            Index("idx_unknown_index_columns_first_second", ["first", "second"]),
        ]

    with pytest.raises(
        TableParsingException,
        match=(
            "Constraint 'idx_unknown_index_columns_first_second' references unknown columns "
            "in table 'unknown_index_columns': second"
        ),
    ):
        parse(UnknownIndexColumn)
