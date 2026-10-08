from server.persistence.repository.sql.ast.data_types import DataType
from server.persistence.repository.sql.ast.nodes.check_constraint_node import CheckConstraintNode
from server.persistence.repository.sql.ast.nodes.column_node import ColumnNode
from server.persistence.repository.sql.ast.nodes.foreign_key_node import ForeignKeyNode
from server.persistence.repository.sql.ast.nodes.index_node import IndexNode
from server.persistence.repository.sql.ast.nodes.postgres_visitor import PostgresVisitor
from server.persistence.repository.sql.ast.nodes.primary_key_node import PrimaryKeyNode
from server.persistence.repository.sql.ast.nodes.table_node import TableNode
from server.persistence.repository.sql.ast.nodes.unique_constraint_node import (
    UniqueCheckConstraintNode,
)

# DataType members render as their Postgres type names


def accounts_table() -> TableNode:
    return TableNode("accounts", [ColumnNode("id", DataType.TEXT, nullable=False)])


def test_rewrite_creates_table_with_columns() -> None:
    table = TableNode(
        "users",
        [ColumnNode("id", DataType.TEXT, nullable=False), ColumnNode("name", DataType.TEXT, nullable=True)],
    )

    create, update = PostgresVisitor.rewrite(table)

    assert create == (
        "CREATE TABLE users (\n"
        "id TEXT NOT NULL,\n"
        "name TEXT\n"
        ");"
    )
    assert update == ""


def test_rewrite_adds_primary_key_constraint() -> None:
    user_id = ColumnNode("id", DataType.TEXT, nullable=False)
    table = TableNode("users", [user_id], primary_key=PrimaryKeyNode("pk_users_id", [user_id]))

    _, update = PostgresVisitor.rewrite(table)

    assert update == (
        "ALTER TABLE users \n"
        "ADD CONSTRAINT pk_users_id PRIMARY KEY (id)\n"
    )


def test_rewrite_adds_foreign_key_constraint() -> None:
    accounts = accounts_table()
    account_id = ColumnNode("account_id", DataType.TEXT, nullable=True)
    table = TableNode(
        "users",
        [account_id],
        foreign_keys=[
            ForeignKeyNode("fk_users_account_id", [account_id], (accounts, accounts.columns))
        ],
    )

    _, update = PostgresVisitor.rewrite(table)

    assert update == (
        "ALTER TABLE users \n"
        "ADD CONSTRAINT fk_users_account_id FOREIGN KEY (account_id) REFERENCES accounts (id)\n"
    )


def test_rewrite_adds_unique_constraint() -> None:
    email = ColumnNode("email", DataType.TEXT, nullable=True)
    table = TableNode(
        "users",
        [email],
        unique_constraints=[UniqueCheckConstraintNode("uq_users_email", [email])],
    )

    _, update = PostgresVisitor.rewrite(table)

    assert update == (
        "ALTER TABLE users \n"
        "ADD CONSTRAINT uq_users_email UNIQUE (email)\n"
    )


def test_rewrite_adds_check_constraint() -> None:
    table = TableNode(
        "products",
        [ColumnNode("price", DataType.INTEGER, nullable=True)],
        check_constraints=[CheckConstraintNode("chk_products_price", "price > 0")],
    )

    _, update = PostgresVisitor.rewrite(table)

    assert update == (
        "ALTER TABLE products \n"
        "ADD CONSTRAINT chk_products_price CHECK (price > 0)\n"
    )


def test_rewrite_creates_indexes_on_the_table() -> None:
    email = ColumnNode("email", DataType.TEXT, nullable=True)
    table = TableNode("users", [email], indexes=[IndexNode("idx_users_email", [email])])

    create, update = PostgresVisitor.rewrite(table)

    assert create == (
        "CREATE TABLE users (\n"
        "email TEXT\n"
        ");"
        "CREATE INDEX idx_users_email ON users (email);"
    )
    assert update == ""


def test_rewrite_adds_every_constraint_in_one_alter_statement() -> None:
    accounts = accounts_table()
    user_id = ColumnNode("id", DataType.TEXT, nullable=False)
    account_id = ColumnNode("account_id", DataType.TEXT, nullable=True)
    email = ColumnNode("email", DataType.TEXT, nullable=True)
    age = ColumnNode("age", DataType.INTEGER, nullable=True)
    table = TableNode(
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

    create, update = PostgresVisitor.rewrite(table)

    assert create == (
        "CREATE TABLE users (\n"
        "id TEXT NOT NULL,\n"
        "account_id TEXT,\n"
        "email TEXT,\n"
        "age INTEGER\n"
        ");"
        "CREATE INDEX idx_users_email ON users (email);"
    )
    assert update == (
        "ALTER TABLE users \n"
        "ADD CONSTRAINT pk_users_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT uq_users_email UNIQUE (email),\n"
        "ADD CONSTRAINT fk_users_account_id FOREIGN KEY (account_id) REFERENCES accounts (id),\n"
        "ADD CONSTRAINT chk_users_age CHECK (age >= 18)\n"
    )
