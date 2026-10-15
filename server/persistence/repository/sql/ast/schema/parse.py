
import dataclasses
import re

from typing import cast, get_type_hints

from models.base.entity import IdEntity

from ...schema.types import PrimaryKey
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
        entity_type = next(e for e in entities if e.table_name == table.name)
        foreign_keys, primary_key, unique_constraints, check_constraints, indexes = _parse_field_constraints(table, entity_type, column_metadata, tables_by_name)

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
    if not hasattr(entity_type, "table_name") or not entity_type.table_name:
        raise TableParsingException(f"Entity '{entity_type.__name__}' must have a table_name attribute")
    table_name = entity_type.table_name

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

def _resolve_columns(table: TableNode, column_names: list[str], constraint_name: str) -> list[ColumnNode]:
    """
    Map the column names used by table level metadata onto the table's columns.
    """
    columns_by_name = {column.name: column for column in table.columns}
    unknown_columns = [name for name in column_names if name not in columns_by_name]
    if unknown_columns:
        raise TableParsingException(f"Constraint '{constraint_name}' references unknown columns in table '{table.name}': {', '.join(unknown_columns)}")
    return [columns_by_name[name] for name in column_names]

def _parse_field_constraints(table: TableNode, entity_type: type[IdEntity], column_metadata: dict[ColumnNode, dict[str, object]], tables_by_name: dict[str, TableNode]) -> tuple[
    list[ForeignKeyNode] | None, 
    PrimaryKeyNode | None, 
    list[UniqueCheckConstraintNode] | None, 
    list[CheckConstraintNode] | None, 
    list[IndexNode] | None, 
]:
    foreign_key_nodes: list[ForeignKeyNode] = []
    primary_key_node: PrimaryKeyNode | None = None
    unique_constraint_nodes: list[UniqueCheckConstraintNode] = []
    check_constraint_nodes: list[CheckConstraintNode] = []
    index_nodes: list[IndexNode] = []

    # PK
    table_pk = entity_type.primary_key if hasattr(entity_type, "primary_key") else None
    column_pks = [column for column, metadata in column_metadata.items() if metadata.get("primary_key")]
    if len(column_pks) > 1:
        raise FieldParsingException(f"Multiple primary keys defined for table '{table.name}': {', '.join(c.name for c in column_pks)}")
    column_pk = column_pks[0] if column_pks else None
    # reconcile table and column primary keys
    match (column_pk, table_pk):
        case (None, None):
            pass
        case (None, _):
            table_pk = cast(PrimaryKey, table_pk)
            name = table_pk.name
            columns = _resolve_columns(table, table_pk.columns, name)
            primary_key_node = PrimaryKeyNode(name, columns)
        case (_, None):
            name = f"pk_{table.name}_{column_pk.name}"
            primary_key_node = PrimaryKeyNode(name, [column_pk])
        case (_, _):
            raise FieldParsingException(f"Conflicting primary key definitions for table '{table.name}': table defines '{table_pk}', column defines '{column_pk.name}'")

    # FK
    table_fks = entity_type.foreign_keys if hasattr(entity_type, "foreign_keys") else None
    column_fks = [column for column, metadata in column_metadata.items() if metadata.get("foreign_key")]
    # Table fks might contain composite fks or single column fks
    # column fks only contains single column fks. We need to throw if there is any overlap with single column table fks and column fks.
    single_column_table_fks = [fk for fk in table_fks if len(fk.source_columns) == 1] if table_fks else []
    composite_table_fks = [fk for fk in table_fks if len(fk.source_columns) > 1] if table_fks else []
    overlapping_fks = [column for column in column_fks if any(fk.source_columns[0] == column.name for fk in single_column_table_fks)]
    if overlapping_fks:
        raise FieldParsingException(f"Conflicting foreign key definitions for table '{table.name}': column fks overlap with single column table fks for columns '{', '.join(c.name for c in overlapping_fks)}'")

    # map single column table fks and composite table fks to foreign key nodes
    for fk in [*single_column_table_fks, *composite_table_fks]:
        name = fk.name
        columns = _resolve_columns(table, fk.source_columns, name)
        if fk.referenced_table not in tables_by_name:
            raise TableParsingException(f"Foreign key table '{fk.referenced_table}' not found for foreign key '{name}' in table '{table.name}'")
        reference_table = tables_by_name[fk.referenced_table]
        # order ref columns by fk.referenced_columns
        reference_columns = [c for c in reference_table.columns if c.name in fk.referenced_columns]
        reference_columns.sort(key=lambda c: fk.referenced_columns.index(c.name))
        if len(reference_columns) != len(fk.referenced_columns):
            missing_columns = set(fk.referenced_columns) - {c.name for c in reference_columns}
            raise FieldParsingException(f"Referenced columns for foreign key '{name}' do not match the expected columns in table '{reference_table.name}'. Missing columns: {', '.join(missing_columns)}")
        if len(columns) != len(reference_columns):
            raise TableParsingException(f"Foreign key '{name}' in table '{table.name}' has {len(columns)} source columns but {len(reference_columns)} referenced columns")
        foreign_key_node = ForeignKeyNode(name, columns, (reference_table, reference_columns))
        foreign_key_nodes.append(foreign_key_node)

    # map column fks to foreign key nodes
    for column in column_fks:
        foreign_key = column_metadata[column].get("foreign_key")
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
        foreign_key_nodes.append(ForeignKeyNode(name, [column], (fk_table, [fk_column])))

    # parse unique constraints for the table and its columns
    table_unique_constraints = entity_type.unique_constraints if hasattr(entity_type, "unique_constraints") else None
    column_unique_constraints = [c for c, metadata in column_metadata.items() if metadata.get("unique", False)]
    single_column_table_unique_constraints = [c for c in table_unique_constraints or [] if len(c.columns) == 1]
    multi_column_table_unique_constraints = [c for c in table_unique_constraints or [] if len(c.columns) > 1]
    overlapping_single_column_constraints = [c for c in column_unique_constraints if any(c.name == uc.columns[0] for uc in single_column_table_unique_constraints)]
    if len(overlapping_single_column_constraints) > 0:
        raise TableParsingException(f"Overlapping single-column unique constraints found: {overlapping_single_column_constraints}")

    # map table constraints to constraint nodes
    for uc in [*single_column_table_unique_constraints, *multi_column_table_unique_constraints]:
        # create constraint nodes for each unique constraint
        name = uc.name
        columns = _resolve_columns(table, uc.columns, name)
        unique_constraint_nodes.append(UniqueCheckConstraintNode(name, columns))

    for column in column_unique_constraints:
        name = f"uq_{table.name}_{column.name}"
        unique_constraint_nodes.append(UniqueCheckConstraintNode(name, [column]))
    
    # parse check constraints for the table and its columns
    table_check_constraints = entity_type.check_constraints if hasattr(entity_type, "check_constraints") else []
    column_check_constraints = [(c, metadata["check"]) for c, metadata in column_metadata.items() if metadata.get("check", False)]
    # make sure there's no duplicate constraints
    overlapping_single_column_check_constraints = [c for (c, check_expr) in column_check_constraints if any(str(check_expr) == uc.expression for uc in table_check_constraints)]
    if len(overlapping_single_column_check_constraints) > 0:
        raise TableParsingException(f"Duplicate check constraints found for columns: {', '.join(c.name for c in overlapping_single_column_check_constraints)} in table '{table.name}'")

    for c, check_expr in column_check_constraints:
        name = f"chk_{table.name}_{c.name}"
        check_constraint_nodes.append(CheckConstraintNode(name, str(check_expr)))

    for cc in table_check_constraints:
        name = cc.name
        check_constraint_nodes.append(CheckConstraintNode(name, cc.expression))
    
    # parse indexes for the table and its columns
    table_indexes = entity_type.indexes if hasattr(entity_type, "indexes") else []
    column_indexes = [c for c, metadata in column_metadata.items() if metadata.get("index", False)]
    single_column_indexes = [c for c in table_indexes if len(c.columns) == 1]
    multi_column_indexes = [c for c in table_indexes if len(c.columns) > 1]
    overlapping_single_column_indexes = [c for c in column_indexes if any(c.name == idx.columns[0] for idx in single_column_indexes)]
    if len(overlapping_single_column_indexes) > 0:
        raise TableParsingException(f"Duplicate single-column indexes found for columns: {', '.join(c.name for c in overlapping_single_column_indexes)} in table '{table.name}'")

    for idx in [*single_column_indexes, *multi_column_indexes]:
        name = idx.name
        columns = _resolve_columns(table, idx.columns, name)
        index_nodes.append(IndexNode(name, columns))

    for c in column_indexes:
        name = f"idx_{table.name}_{c.name}"
        index_nodes.append(IndexNode(name, [c]))
    
    return foreign_key_nodes or None, \
           primary_key_node or None, \
           unique_constraint_nodes or None, \
           check_constraint_nodes or None, \
           index_nodes or None
