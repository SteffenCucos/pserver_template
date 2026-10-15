
import sqlite3

import pytest

from server.auth.rbac.models import Permission, Role, RolePermission, UserRole
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
from server.persistence.repository.sql.ast.schema.parse import parse_entities_to_tables
from server.persistence.repository.sql.sqlite.sqlite_type_rewriter import SqliteTypeRewriter
from server.persistence.repository.sql.sqlite.sqlite_visitor import SqliteVisitor
from server.users.user import User


def accounts_table() -> TableNode:
    return TableNode("accounts", [ColumnNode("id", DataType.TEXT, nullable=False)])


def test_rewrite_creates_table_with_columns() -> None:
    table = TableNode(
        "users",
        [ColumnNode("id", DataType.TEXT, nullable=False), ColumnNode("name", DataType.TEXT, nullable=True)],
    )

    statements = SqliteVisitor.rewrite(table)

    assert statements == [
        "CREATE TABLE users (\n"
        "id TEXT NOT NULL,\n"
        "name TEXT\n"
        ");"
    ]


def test_rewrite_declares_primary_key_inline() -> None:
    user_id = ColumnNode("id", DataType.TEXT, nullable=False)
    table = TableNode("users", [user_id], primary_key=PrimaryKeyNode("pk_users_id", [user_id]))

    statements = SqliteVisitor.rewrite(table)

    assert statements == [
        "CREATE TABLE users (\n"
        "id TEXT NOT NULL,\n"
        "CONSTRAINT pk_users_id PRIMARY KEY (id)\n"
        ");"
    ]


def test_rewrite_declares_foreign_key_inline() -> None:
    accounts = accounts_table()
    account_id = ColumnNode("account_id", DataType.TEXT, nullable=True)
    table = TableNode(
        "users",
        [account_id],
        foreign_keys=[
            ForeignKeyNode("fk_users_account_id", [account_id], (accounts, accounts.columns))
        ],
    )

    statements = SqliteVisitor.rewrite(table)

    assert statements == [
        "CREATE TABLE users (\n"
        "account_id TEXT,\n"
        "CONSTRAINT fk_users_account_id FOREIGN KEY (account_id) REFERENCES accounts (id)\n"
        ");"
    ]


def test_rewrite_declares_unique_constraint_inline() -> None:
    email = ColumnNode("email", DataType.TEXT, nullable=True)
    table = TableNode(
        "users",
        [email],
        unique_constraints=[UniqueCheckConstraintNode("uq_users_email", [email])],
    )

    statements = SqliteVisitor.rewrite(table)

    assert statements == [
        "CREATE TABLE users (\n"
        "email TEXT,\n"
        "CONSTRAINT uq_users_email UNIQUE (email)\n"
        ");"
    ]


def test_rewrite_declares_check_constraint_inline() -> None:
    table = TableNode(
        "products",
        [ColumnNode("price", DataType.INTEGER, nullable=True)],
        check_constraints=[CheckConstraintNode("chk_products_price", "price > 0")],
    )

    statements = SqliteVisitor.rewrite(table)

    assert statements == [
        "CREATE TABLE products (\n"
        "price INTEGER,\n"
        "CONSTRAINT chk_products_price CHECK (price > 0)\n"
        ");"
    ]


def test_rewrite_returns_each_index_as_a_separate_statement() -> None:
    email = ColumnNode("email", DataType.TEXT, nullable=True)
    name = ColumnNode("name", DataType.TEXT, nullable=True)
    table = TableNode(
        "users",
        [email, name],
        indexes=[IndexNode("idx_users_email", [email]), IndexNode("idx_users_name", [name])],
    )

    statements = SqliteVisitor.rewrite(table)

    assert statements == [
        "CREATE TABLE users (\n"
        "email TEXT,\n"
        "name TEXT\n"
        ");",
        "CREATE INDEX idx_users_email ON users (email);",
        "CREATE INDEX idx_users_name ON users (name);",
    ]


@pytest.mark.parametrize(
    ("data_type", "expected"),
    [
        (DataType.INTEGER, DataType.INTEGER),
        (DataType.BOOLEAN, DataType.INTEGER),
        (DataType.DOUBLE_PRECISION, "REAL"),
        (DataType.TEXT, DataType.TEXT),
        (DataType.TIMESTAMP, DataType.TEXT),
        (DataType.JSON, DataType.TEXT),
    ],
)
def test_type_rewriter_maps_to_sqlite_types(data_type: DataType, expected: str) -> None:
    table = TableNode("t", [ColumnNode("c", data_type, nullable=False)])

    rewritten = SqliteTypeRewriter.rewrite(table)

    assert rewritten.columns[0].type == expected


def test_generated_ddl_executes_against_sqlite() -> None:
    connection = sqlite3.connect(":memory:")

    for table in parse_entities_to_tables([Permission, Role, RolePermission, User, UserRole]):
        for statement in SqliteVisitor.rewrite(SqliteTypeRewriter.rewrite(table)):
            connection.execute(statement)

    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tables == {"permissions", "roles", "role_permissions", "users", "user_roles"}
