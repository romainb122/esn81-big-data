"""Schema for the first, technical comparison runs."""

import pyarrow as pa
from pyiceberg.schema import Schema
from pyiceberg.types import DoubleType, LongType, NestedField, StringType

COMPARISON_SCHEMA = pa.schema([
    pa.field("comparison_id", pa.string()),
    pa.field("prompt", pa.string()),
    pa.field("harness", pa.string()),
    pa.field("provider", pa.string()),
    pa.field("model", pa.string()),
    pa.field("input_tokens", pa.int64()),
    pa.field("output_tokens", pa.int64()),
    pa.field("total_tokens", pa.int64()),
    pa.field("cost", pa.float64()),
    pa.field("duration_ms", pa.int64()),
    pa.field("temperature", pa.float64()),
    pa.field("context_window", pa.int64()),
    pa.field("context_used", pa.int64()),
    pa.field("created_at_ms", pa.int64()),
    pa.field("status", pa.string()),
    pa.field("response", pa.string()),
    pa.field("error", pa.string()),
])


def iceberg_schema():
    types = {
        pa.types.is_int64: LongType,
        pa.types.is_float64: DoubleType,
    }
    fields = []
    for field_id, field in enumerate(COMPARISON_SCHEMA, start=1):
        field_type = next((factory() for predicate, factory in types.items() if predicate(field.type)), StringType())
        fields.append(NestedField(field_id, field.name, field_type, required=False))
    return Schema(*fields)
