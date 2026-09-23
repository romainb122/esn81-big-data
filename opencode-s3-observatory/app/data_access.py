import os

import streamlit as st
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchTableError


EVENT_METADATA_FIELDS = (
    "session_id",
    "session_title",
    "session_agent",
    "session_provider_id",
    "session_model_id",
    "session_model_variant",
    "session_cost",
    "session_tokens_input",
    "session_tokens_output",
    "session_tokens_reasoning",
    "session_tokens_cache_read",
    "session_tokens_cache_write",
    "exported_at_ms",
    "message_id",
    "event_id",
    "event_index",
    "event_type",
    "role",
    "message_created_ms",
    "message_completed_ms",
    "agent",
    "provider_id",
    "model_id",
    "tool_name",
    "tool_title",
    "tool_status",
)


def iceberg_catalog():
    return load_catalog(
        "opencode",
        type="rest",
        uri=os.environ.get("ICEBERG_URI", "http://localhost:8181"),
        warehouse=f"s3://{os.environ.get('S3_BUCKET', 'bigdata')}/iceberg/",
        **{
            "s3.endpoint": os.environ.get("S3_ENDPOINT", "http://s3:8333"),
            "s3.access-key-id": os.environ["AWS_ACCESS_KEY_ID"],
            "s3.secret-access-key": os.environ["AWS_SECRET_ACCESS_KEY"],
            "s3.region": os.environ.get("AWS_REGION", "us-east-1"),
            "s3.path-style-access": "true",
        },
    )


def iceberg_literal(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


@st.cache_data(ttl=60, show_spinner="Lecture de l'index Iceberg dans S3...")
def load_event_metadata():
    """Load only the lightweight columns needed to browse sessions."""
    try:
        return iceberg_catalog().load_table("opencode.events").scan(selected_fields=EVENT_METADATA_FIELDS).to_arrow()
    except NoSuchTableError:
        return None


@st.cache_data(ttl=60, show_spinner="Chargement des messages...")
def load_thread_page(session_id, message_ids):
    """Load complete event data only for one visible page of messages."""
    if not message_ids:
        return None
    quoted_ids = ", ".join(iceberg_literal(message_id) for message_id in message_ids)
    row_filter = f"session_id = {iceberg_literal(session_id)} AND message_id IN ({quoted_ids})"
    return iceberg_catalog().load_table("opencode.events").scan(row_filter=row_filter).to_arrow()
