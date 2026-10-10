
import dataclasses
import re

from typing import get_type_hints

from models.base.entity import IdEntity

from .data_types import DataType
from .exceptions import FieldParsingException, TableParsingException
from .nodes.check_constraint_node import CheckConstraintNode
from .nodes.column_node import ColumnNode
from .nodes.foreign_key_node import ForeignKeyNode
from .nodes.index_node import IndexNode
from .nodes.primary_key_node import PrimaryKeyNode
from .nodes.table_node import TableNode
from .nodes.unique_constraint_node import UniqueCheckConstraintNode


_foreign_key_pattern = re.compile(
    r"(?P<table>[A-Za-z_][A-Za-z0-9_]*)\.(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
)


def parse_entities_to_tables(entities: list[type[IdEntity]]) -> list[TableNode]:
    partially_resolved_tables_with_metadata = list(map(_parse_entity_to_partial_table, entities))
    partially_resolved_tables = [table for table, _ in partially_resolved_tables_with_metadata]
    tables_by_name: dict[str, TableNode] = {table.name: table for table in partially_resolved_tables}
    table_to_column_metadata: dict[TableNode, dict[ColumnNode, dict[str, object]]] = {
        table: column_metadata for (table, column_metadata) in partially_resolved_tables_with_metadata
    }

    for table in partially_resolved_tables:
        column_metadata = table_to_column_metadata[table]
        foreign_keys, primary_key, unique_constraints, check_constraints, indexes = _parse_field_constraints(table, column_metadata, tables_by_name)

        table.foreign_keys = foreign_keys
        table.primary_key = primary_key
        table.unique_constraints = unique_constraints
        table.check_constraints = check_constraints
        table.indexes = indexes

    # FKs are now resolved
    fully_resolved_tables = partially_resolved_tables
    return fully_resolved_tables


def _parse_entity_to_partial_table(entity_type: type[IdEntity]) -> tuple[TableNode, dict[ColumnNode, dict[str, object]]]:
    """
    First pass where we establish the table name and fields, but we haven't considered relationships yet.
    """
    table_name = entity_type.table_name()

    columns = []
    metadata_by_column: dict[ColumnNode, dict[str, object]] = {}
    # Loop over the fields of the entity
    hints = get_type_hints(entity_type)
    for dataclass_field in entity_type.iterate_field_metadata():
        column, column_metadata = _parse_field_to_column(dataclass_field, hints)
        metadata_by_column[column] = column_metadata
        columns.append(column)

    return (TableNode(table_name, columns), metadata_by_column)

def _parse_field_to_column(dataclass_field: dataclasses.Field[str], hints: dict[str, type]) -> tuple[ColumnNode, dict[str, object]]:
    column_name = dataclass_field.name
    field_type = hints[column_name]
    field_metadata = dataclass_field.metadata
    # None when the metadata doesn't specify nullability
    metadata_nullable = dataclass_field.metadata.get("nullable")
    column_type, nullable = DataType.from_python_type(field_type)
    if nullable and metadata_nullable is False:
        raise FieldParsingException(f"Field '{column_name}' is marked as non nullable in its metadata but is typed as nullable in its class declaration")
    if not nullable and metadata_nullable:
        nullable = True
    return (ColumnNode(column_name, column_type, nullable), dict(**field_metadata))

def _parse_field_constraints(table: TableNode, column_metadata: dict[ColumnNode, dict[str, object]], tables_by_name: dict[str, TableNode]) -> tuple[
    list[ForeignKeyNode] | None, 
    PrimaryKeyNode | None, 
    list[UniqueCheckConstraintNode] | None, 
    list[CheckConstraintNode] | None, 
    list[IndexNode] | None, 
]:
    foreign_keys, primary_key, unique_constraints, check_constraints, indexes = [], None, [], [], []

    for column, metadata in column_metadata.items():
        if foreign_key := metadata.get("foreign_key"):
            if not isinstance(foreign_key, str):
                raise TableParsingException("Foreign key must be a string of the form 'table.field'")

            match = _foreign_key_pattern.fullmatch(foreign_key)
            if match is None:
                raise TableParsingException("Foreign key must be a string of the form 'table.field'")

            fk_table_name, fk_field_name = match["table"], match["field"]
            if fk_table_name not in tables_by_name:
                raise TableParsingException(f"Foreign key table '{fk_table_name}' not found for field '{column.name}' in table '{table.name}'")

            fk_table = tables_by_name[fk_table_name]
            fk_column = next((c for c in fk_table.columns if c.name == fk_field_name), None)
            if fk_column is None:
                raise TableParsingException(f"Foreign key field '{fk_field_name}' not found in table '{fk_table_name}' for field '{column.name}' in table '{table.name}'")

            name = f"fk_{table.name}_{column.name}"
            foreign_keys.append(ForeignKeyNode(name, [column], (fk_table, [fk_column])))
        if metadata.get("primary_key", False):
            if primary_key is not None:
                raise TableParsingException(f"Multiple primary keys defined for table '{table.name}', column '{column.name}' & '{primary_key.columns[0].name}'") 
            name = f"pk_{table.name}_{column.name}"
            primary_key = PrimaryKeyNode(name, [column])
        if metadata.get("unique", False):
            name = f"uq_{table.name}_{column.name}"
            unique_constraints.append(UniqueCheckConstraintNode(name, [column]))
        if check := metadata.get("check"):
            name = f"chk_{table.name}_{column.name}"
            check_constraints.append(CheckConstraintNode(name, str(check)))
        if metadata.get("index", False):
            index_name = f"idx_{table.name}_{column.name}"
            indexes.append(IndexNode(index_name, [column]))

    return foreign_keys or None, \
           primary_key or None, \
           unique_constraints or None, \
           check_constraints or None, \
           indexes or None
