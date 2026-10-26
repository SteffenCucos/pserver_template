
from server.persistence.models.field import FieldMetadata, cfield


def test_field_metadata_merge():
    metadata1 = FieldMetadata(nullable=True, index=True, complex={"a": 1, "b": 3})
    metadata2 = FieldMetadata(unique=True, index=False, complex={"a": 2})

    merged_metadata = metadata1 + metadata2

    assert merged_metadata._metadata["nullable"] is True
    assert merged_metadata._metadata["unique"] is True
    assert merged_metadata._metadata["index"] is True  # Bools are OR'd, so True | False = True
    assert merged_metadata._metadata["complex"] == {"a": 2, "b": 3}  # The 'other' value should overwrite the first one

def test_cfield_merges_metadata():
    metadata1 = FieldMetadata(nullable=True, index=True, complex={"a": 1, "b": 3})
    metadata2 = FieldMetadata(unique=True, index=False, complex={"a": 2})

    field = cfield(metadata1, metadata2, default=42)

    assert field.metadata["nullable"] is True
    assert field.metadata["unique"] is True
    assert field.metadata["index"] is True  # Bools are OR'd, so True | False = True
    assert field.metadata["complex"] == {"a": 2, "b": 3}  # The 'other' value should overwrite the first one
    assert field.default == 42
