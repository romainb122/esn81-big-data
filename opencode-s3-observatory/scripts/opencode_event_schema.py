"""Shared Arrow and Iceberg schemas for visible conversation events."""

import pyarrow as pa
from pyiceberg.schema import Schema
from pyiceberg.types import DoubleType, LongType, NestedField, StringType


SCHEMA = pa.schema(
    [
        pa.field("session_id", pa.string()),
        pa.field("session_title", pa.string()),
        pa.field("session_created_ms", pa.int64()),
        pa.field("session_updated_ms", pa.int64()),
        pa.field("session_agent", pa.string()),
        pa.field("session_provider_id", pa.string()),
        pa.field("session_model_id", pa.string()),
        pa.field("session_model_variant", pa.string()),
        pa.field("session_cost", pa.float64()),
        pa.field("session_tokens_input", pa.int64()),
        pa.field("session_tokens_output", pa.int64()),
        pa.field("session_tokens_reasoning", pa.int64()),
        pa.field("session_tokens_cache_read", pa.int64()),
        pa.field("session_tokens_cache_write", pa.int64()),
        pa.field("exported_at_ms", pa.int64()),
        pa.field("message_id", pa.string()),
        pa.field("event_id", pa.string()),
        pa.field("event_index", pa.int64()),
        pa.field("event_type", pa.string()),
        pa.field("role", pa.string()),
        pa.field("message_created_ms", pa.int64()),
        pa.field("message_completed_ms", pa.int64()),
        pa.field("agent", pa.string()),
        pa.field("provider_id", pa.string()),
        pa.field("model_id", pa.string()),
        pa.field("content", pa.string()),
        pa.field("tool_name", pa.string()),
        pa.field("tool_title", pa.string()),
        pa.field("tool_status", pa.string()),
        pa.field("tool_input_json", pa.string()),
        pa.field("tool_output", pa.string()),
        pa.field("details_json", pa.string()),
    ]
)


def iceberg_schema():
    fields = []
    for field_id, field in enumerate(SCHEMA, start=1):
        if pa.types.is_int64(field.type):
            field_type = LongType()
        elif pa.types.is_float64(field.type):
            field_type = DoubleType()
        else:
            field_type = StringType()
        fields.append(NestedField(field_id=field_id, name=field.name, field_type=field_type, required=False))
    return Schema(*fields)
