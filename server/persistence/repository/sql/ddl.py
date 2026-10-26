
from models.base.entity import IdEntity

from .ast.schema.parse import parse_entities_to_tables
from .ast.schema.schema_generator import SchemaGenerator
from .ast.schema.table_rewriter import TableRewriter
from .postgres.postgres_schema_generator import PostgresSchemaGenerator
from .postgres.postgres_type_rewriter import PostgresTypeRewriter


def generate_schema_ddl_operations(entity_types: list[type[IdEntity]]) -> list[str]:
    """
    Generate a list of DDL statements for creating tables and establishing relationships based on the provided entity types.
    """

    type_rewriter: TableRewriter = PostgresTypeRewriter()
    schema_generator: SchemaGenerator = PostgresSchemaGenerator()

    create_ddl, update_ddl = [], []
    for table in parse_entities_to_tables(entity_types):
        type_rewriten_table = type_rewriter.rewrite(table)
        create, update = schema_generator.rewrite(type_rewriten_table)
        create_ddl.append(create)
        update_ddl.append(update)

    return [*create_ddl, "\n", *update_ddl]
