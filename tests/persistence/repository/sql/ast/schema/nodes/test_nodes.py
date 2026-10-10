
from collections.abc import Callable
from typing import override

import pytest

from server.persistence.repository.sql.ast.schema.data_types import DataType
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
from server.persistence.repository.sql.ast.schema.nodes.visitable import Visitable
from server.persistence.repository.sql.ast.schema.schema_visitor import SchemaVisitor


class RecordingVisitor(SchemaVisitor):
    """
    Records each visit as (node kind, node name)
    """

    def __init__(self) -> None:
        self.visits: list[tuple[str, str]] = []

    @override
    def visit_column(self, column: ColumnNode) -> None:
        self.visits.append(("column", column.name))

    @override
    def visit_table(self, table: TableNode) -> None:
        self.visits.append(("table", table.name))

    @override
    def visit_primary_key(self, primary_key: PrimaryKeyNode) -> None:
        self.visits.append(("primary_key", primary_key.name))

    @override
    def visit_unique_constraint(self, unique_constraint: UniqueCheckConstraintNode) -> None:
        self.visits.append(("unique_constraint", unique_constraint.name))

    @override
    def visit_foreign_key(self, foreign_key: ForeignKeyNode) -> None:
        self.visits.append(("foreign_key", foreign_key.name))

    @override
    def visit_check_constraint(self, constraint: CheckConstraintNode) -> None:
        self.visits.append(("check_constraint", constraint.name))

    @override
    def visit_index(self, index: IndexNode) -> None:
        self.visits.append(("index", index.name))


def accounts_table() -> TableNode:
    return TableNode("accounts", [ColumnNode("id", DataType.TEXT, nullable=False)])


def users_table() -> TableNode:
    accounts = accounts_table()
    user_id = ColumnNode("id", DataType.TEXT, nullable=False)
    account_id = ColumnNode("account_id", DataType.TEXT, nullable=True)
    email = ColumnNode("email", DataType.TEXT, nullable=True)
    age = ColumnNode("age", DataType.INTEGER, nullable=True)

    return TableNode(
        "users",
        [user_id, account_id, email, age],
        primary_key=PrimaryKeyNode("pk_users_id", [user_id]),
        foreign_keys=[
            ForeignKeyNode("fk_users_account_id", [account_id], (accounts, accounts.columns))
        ],
        unique_constraints=[UniqueCheckConstraintNode("uq_users_email", [email])],
        check_constraints=[CheckConstraintNode("chk_users_age", "age >= 18")],
        indexes=[IndexNode("idx_users_email", [email])],
    )


@pytest.mark.parametrize(
    ("make_node", "expected_visit"),
    [
        pytest.param(lambda: ColumnNode("email", DataType.TEXT, nullable=True), ("column", "email"), id="column"),
        pytest.param(
            lambda: PrimaryKeyNode("pk_users_id", [ColumnNode("id", DataType.TEXT, nullable=True)]),
            ("primary_key", "pk_users_id"),
            id="primary_key",
        ),
        pytest.param(
            lambda: UniqueCheckConstraintNode("uq_users_email", [ColumnNode("email", DataType.TEXT, nullable=True)]),
            ("unique_constraint", "uq_users_email"),
            id="unique_constraint",
        ),
        pytest.param(
            lambda: ForeignKeyNode(
                "fk_users_account_id",
                [ColumnNode("account_id", DataType.TEXT, nullable=True)],
                (accounts_table(), accounts_table().columns),
            ),
            ("foreign_key", "fk_users_account_id"),
            id="foreign_key",
        ),
        pytest.param(
            lambda: CheckConstraintNode("chk_users_age", "age >= 18"),
            ("check_constraint", "chk_users_age"),
            id="check_constraint",
        ),
        pytest.param(
            lambda: IndexNode("idx_users_email", [ColumnNode("email", DataType.TEXT, nullable=True)]),
            ("index", "idx_users_email"),
            id="index",
        ),
        pytest.param(lambda: TableNode("users", []), ("table", "users"), id="table"),
    ],
)
def test_accept_dispatches_to_matching_visit_method(
    make_node: Callable[[], Visitable], expected_visit: tuple[str, str]
) -> None:
    visitor = RecordingVisitor()

    make_node().accept(visitor)

    assert visitor.visits == [expected_visit]


def test_table_accept_visits_every_child_node_and_the_table() -> None:
    visitor = RecordingVisitor()

    users_table().accept(visitor)

    assert sorted(visitor.visits) == sorted([
        ("column", "id"),
        ("column", "account_id"),
        ("column", "email"),
        ("column", "age"),
        ("primary_key", "pk_users_id"),
        ("unique_constraint", "uq_users_email"),
        ("foreign_key", "fk_users_account_id"),
        ("check_constraint", "chk_users_age"),
        ("index", "idx_users_email"),
        ("table", "users"),
    ])


def test_foreign_key_allows_referencing_a_differently_named_column() -> None:
    accounts = accounts_table()
    account_id = ColumnNode("account_id", DataType.TEXT, nullable=True)

    foreign_key = ForeignKeyNode("fk_users_account_id", [account_id], (accounts, accounts.columns))

    assert foreign_key.columns == [account_id]
    assert foreign_key.references == (accounts, accounts.columns)


@pytest.mark.parametrize(
    ("columns", "references", "message"),
    [
        pytest.param(
            [],
            (accounts_table(), [ColumnNode("id", DataType.TEXT, nullable=True)]),
            "must have at least one column",
            id="no_columns",
        ),
        pytest.param(
            [ColumnNode("account_id", DataType.TEXT, nullable=True)],
            (None, [ColumnNode("id", DataType.TEXT, nullable=True)]),
            "must reference a table",
            id="no_table",
        ),
        pytest.param(
            [ColumnNode("account_id", DataType.TEXT, nullable=True)],
            (accounts_table(), []),
            "must have at least one reference",
            id="no_referenced_columns",
        ),
        pytest.param(
            [ColumnNode("account_id", DataType.TEXT, nullable=True), ColumnNode("region", DataType.TEXT, nullable=True)],
            (accounts_table(), [ColumnNode("id", DataType.TEXT, nullable=True)]),
            "number of columns and references must match",
            id="column_count_mismatch",
        ),
        pytest.param(
            [ColumnNode("account_id", DataType.INTEGER, nullable=True)],
            (accounts_table(), [ColumnNode("id", DataType.TEXT, nullable=True)]),
            "types must match",
            id="column_type_mismatch",
        ),
    ],
)
def test_foreign_key_rejects_invalid_definitions(
    columns: list[ColumnNode],
    references: tuple[TableNode, list[ColumnNode]],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ForeignKeyNode("fk_users_account_id", columns, references)
