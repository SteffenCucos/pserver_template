
from dataclasses import MISSING, field
from typing import Any, Callable


class FieldMetadata():
    """
    Holds a list metadata name+value pairs, supprots merging with 
    other FieldMetadata objects to more easily combine sets of metadata

    Ex:
    min = FieldMetadata(min=0)
    max = FieldMetadata(max=10)

    min | max == FieldMetadata(min=0,max=10)
    """

    def __init__(self, **kwargs: Any):
        self._metadata = {**kwargs}

    def __add__(self, other: 'FieldMetadata') -> 'FieldMetadata':
        return self._merge(other)

    def __or__(self, other: 'FieldMetadata') -> 'FieldMetadata':
        return self._merge(other)

    def _merge(self, other: 'FieldMetadata') -> 'FieldMetadata':
        combined_metadata = {**self._metadata}
        for key in combined_metadata.keys():
            value = combined_metadata[key]
            if key in other._metadata.keys():
                other_value = other._metadata[key]
                if isinstance(value, dict):
                    value = {**value, **other_value} # The 'other' will overwrite any fields they share
                if isinstance(value, bool):
                    value = value or other_value

            combined_metadata[key] = value

        for key in other._metadata.keys():
            if key not in combined_metadata.keys():
                combined_metadata[key] = other._metadata[key]
                
        return FieldMetadata(**combined_metadata)


def cfield(
    *metadata_items: FieldMetadata,
    default: Any = MISSING,
    default_factory: Callable[[], Any] | Any = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    kw_only: bool = False
) -> Any:
    merged_field_metadata = FieldMetadata()

    for item in metadata_items:
        merged_field_metadata = merged_field_metadata | item

    merged_metadata = merged_field_metadata._metadata

    return field(
        default=default,
        default_factory=default_factory,
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
        metadata=merged_metadata,
        kw_only=kw_only,
    )
