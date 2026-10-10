
from models.base.entity import IdEntity

from .ast.schema.parse import parse_entities_to_tables
from .postgres.postgres_type_rewriter import PostgresTypeRewriter
from .postgres.postgres_visitor import PostgresVisitor


def generate_schema_ddl_operations(entity_types: list[type[IdEntity]]) -> list[str]:
    """
    Generate a list of DDL statements for creating tables and establishing relationships based on the provided entity types.
    """

    create_ddl, update_ddl = [], []
    for table in parse_entities_to_tables(entity_types):
        pg_table = PostgresTypeRewriter.rewrite(table)
        create, update = PostgresVisitor.rewrite(pg_table)
        create_ddl.append(create)
        update_ddl.append(update)

    return create_ddl + ["\n"] + update_ddl
