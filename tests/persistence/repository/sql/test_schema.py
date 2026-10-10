
from dataclasses import dataclass
from datetime import datetime
from typing import cast, override

import pytest

from server.auth.rbac.models import Permission, Role, RolePermission, UserRole
from server.models.base.entity import Entity
from server.models.base.id import Id
from server.persistence.models import CHECK, FOREIGN_KEY, UNIQUE, field
from server.persistence.repository.sql.ast.schema.exceptions import TableParsingException
from server.persistence.repository.sql.schema import generate_schema_ddl_operations
from server.users.user import User


# Region Test Types

@dataclass
class TestTypesEntity(Entity()):
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
        return "test_types_entities"


@dataclass
class TestFKEntity(Entity()):
    fk_field: Id = field(FOREIGN_KEY("test_types_entities.id"))

    @override
    @staticmethod
    def table_name() -> str:
        return "test_fk_entities"


@dataclass
class TestUniqueEntity(Entity()):
    unique_field: str = field(UNIQUE)

    @override
    @staticmethod
    def table_name() -> str:
        return "test_unique_entities"


@dataclass
class TestCheckConstraintEntity(Entity()):
    check_field: int = field(CHECK("check_field > 0"))

    @override
    @staticmethod
    def table_name() -> str:
        return "test_check_constraint_entities"


CREATE_TEST_TYPES_ENTITIES = (
    "CREATE TABLE test_types_entities (\n"
    "id TEXT NOT NULL,\n"
    "created_date TIMESTAMP NOT NULL,\n"
    "updated_date TIMESTAMP NOT NULL,\n"
    "date_f TIMESTAMP NOT NULL,\n"
    "float_f DOUBLE PRECISION NOT NULL,\n"
    "int_f INTEGER NOT NULL,\n"
    "str_f TEXT NOT NULL,\n"
    "dict_f JSONB NOT NULL,\n"
    "list_f JSONB NOT NULL,\n"
    "bool_f BOOLEAN NOT NULL\n"
    ");"
)

ALTER_TEST_TYPES_ENTITIES = (
    "ALTER TABLE test_types_entities \n"
    "ADD CONSTRAINT pk_test_types_entities_id PRIMARY KEY (id)\n"
)

# Region Tests

def test_generate_schema_ddl_operations_creates_proper_types() -> None:
    operations = generate_schema_ddl_operations([TestTypesEntity])
    assert operations == [
        CREATE_TEST_TYPES_ENTITIES,
        "\n",
        ALTER_TEST_TYPES_ENTITIES,
    ]


def test_generate_schema_ddl_operations_creates_foreign_keys() -> None:
    operations = generate_schema_ddl_operations([TestTypesEntity, TestFKEntity])
    assert operations == [
        CREATE_TEST_TYPES_ENTITIES,
        "CREATE TABLE test_fk_entities (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "fk_field TEXT NOT NULL\n"
        ");",
        "\n",
        ALTER_TEST_TYPES_ENTITIES,
        "ALTER TABLE test_fk_entities \n"
        "ADD CONSTRAINT pk_test_fk_entities_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT fk_test_fk_entities_fk_field FOREIGN KEY (fk_field) "
        "REFERENCES test_types_entities (id)\n",
    ]


def test_generate_schema_ddl_operations_creates_unique_constraints() -> None:
    operations = generate_schema_ddl_operations([TestUniqueEntity])
    assert operations == [
        "CREATE TABLE test_unique_entities (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "unique_field TEXT NOT NULL\n"
        ");",
        "\n",
        "ALTER TABLE test_unique_entities \n"
        "ADD CONSTRAINT pk_test_unique_entities_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT uq_test_unique_entities_unique_field UNIQUE (unique_field)\n",
    ]


def test_generate_schema_ddl_operations_creates_check_constraints() -> None:
    operations = generate_schema_ddl_operations([TestCheckConstraintEntity])
    assert operations == [
        "CREATE TABLE test_check_constraint_entities (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "check_field INTEGER NOT NULL\n"
        ");",
        "\n",
        "ALTER TABLE test_check_constraint_entities \n"
        "ADD CONSTRAINT pk_test_check_constraint_entities_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT chk_test_check_constraint_entities_check_field CHECK (check_field > 0)\n",
    ]


def test_generate_schema_ddl_operations_creates_role_permission_schema() -> None:
    operations = generate_schema_ddl_operations([Permission, Role, RolePermission, User, UserRole])
    assert operations == [
        "CREATE TABLE permissions (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "key TEXT NOT NULL,\n"
        "description TEXT\n"
        ");"
        "CREATE INDEX idx_permissions_key ON permissions (key);",

        "CREATE TABLE roles (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "name TEXT NOT NULL,\n"
        "description TEXT\n"
        ");"
        "CREATE INDEX idx_roles_name ON roles (name);",

        "CREATE TABLE role_permissions (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "role_id TEXT NOT NULL,\n"
        "permission_id TEXT NOT NULL\n"
        ");",

        "CREATE TABLE users (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "user_name TEXT NOT NULL,\n"
        "first_name TEXT NOT NULL,\n"
        "last_name TEXT NOT NULL,\n"
        "password_hash TEXT NOT NULL,\n"
        "email TEXT NOT NULL,\n"
        "email_verified BOOLEAN NOT NULL\n"
        ");"
        "CREATE INDEX idx_users_user_name ON users (user_name);"
        "CREATE INDEX idx_users_email ON users (email);",

        "CREATE TABLE user_roles (\n"
        "id TEXT NOT NULL,\n"
        "created_date TIMESTAMP NOT NULL,\n"
        "updated_date TIMESTAMP NOT NULL,\n"
        "user_id TEXT NOT NULL,\n"
        "role_id TEXT NOT NULL\n"
        ");",

        "\n",

        "ALTER TABLE permissions \n"
        "ADD CONSTRAINT pk_permissions_id PRIMARY KEY (id)\n",

        "ALTER TABLE roles \n"
        "ADD CONSTRAINT pk_roles_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT uq_roles_name UNIQUE (name)\n",

        "ALTER TABLE role_permissions \n"
        "ADD CONSTRAINT pk_role_permissions_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT fk_role_permissions_role_id FOREIGN KEY (role_id) REFERENCES roles (id),\n"
        "ADD CONSTRAINT fk_role_permissions_permission_id FOREIGN KEY (permission_id) "
        "REFERENCES permissions (id)\n",

        "ALTER TABLE users \n"
        "ADD CONSTRAINT pk_users_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT uq_users_email UNIQUE (email)\n",

        "ALTER TABLE user_roles \n"
        "ADD CONSTRAINT pk_user_roles_id PRIMARY KEY (id),\n"
        "ADD CONSTRAINT fk_user_roles_user_id FOREIGN KEY (user_id) REFERENCES users (id),\n"
        "ADD CONSTRAINT fk_user_roles_role_id FOREIGN KEY (role_id) REFERENCES roles (id)\n",
    ]


def test_generate_schema_ddl_operations_rejects_non_string_foreign_keys() -> None:
    @dataclass
    class InvalidForeignKeyEntity(Entity()):
        target_id: Id = field(FOREIGN_KEY(cast(str, 1)))

        @staticmethod
        def table_name() -> str:
            return "invalid_foreign_key_entities"

    with pytest.raises(TableParsingException, match="Foreign key must be a string"):
        generate_schema_ddl_operations([TestTypesEntity, InvalidForeignKeyEntity])


def test_generate_schema_ddl_operations_rejects_malformed_foreign_keys() -> None:
    @dataclass
    class InvalidForeignKeyEntity(Entity()):
        target_id: Id = field(FOREIGN_KEY("test_types_entities-id"))

        @staticmethod
        def table_name() -> str:
            return "invalid_foreign_key_entities"

    with pytest.raises(TableParsingException, match="Foreign key must be a string"):
        generate_schema_ddl_operations([TestTypesEntity, InvalidForeignKeyEntity])


def test_generate_schema_ddl_operations_rejects_foreign_keys_to_unknown_tables() -> None:
    @dataclass
    class InvalidForeignKeyEntity(Entity()):
        target_id: Id = field(FOREIGN_KEY("unknown_table.id"))

        @staticmethod
        def table_name() -> str:
            return "invalid_foreign_key_entities"

    with pytest.raises(TableParsingException, match="Foreign key table 'unknown_table' not found"):
        generate_schema_ddl_operations([TestTypesEntity, InvalidForeignKeyEntity])


def test_generate_schema_ddl_operations_rejects_foreign_keys_to_unknown_fields() -> None:
    @dataclass
    class InvalidForeignKeyEntity(Entity()):
        target_id: Id = field(FOREIGN_KEY("test_types_entities.unknown_id"))

        @staticmethod
        def table_name() -> str:
            return "invalid_foreign_key_entities"

    with pytest.raises(TableParsingException, match="Foreign key field 'unknown_id' not found"):
        generate_schema_ddl_operations([TestTypesEntity, InvalidForeignKeyEntity])
