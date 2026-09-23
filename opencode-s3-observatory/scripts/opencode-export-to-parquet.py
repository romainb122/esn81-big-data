#!/usr/bin/env python3
"""Store visible OpenCode events as JSON and analytics-friendly Parquet."""

import argparse
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


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


def integer(value):
    return value if isinstance(value, int) else None


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def json_value(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def visible_export(exported):
    """Keep user-visible conversation data and omit private reasoning parts."""
    copied = {"info": exported["info"], "messages": []}
    for message in exported.get("messages", []):
        copied["messages"].append(
            {
                "info": message.get("info", {}),
                "parts": [part for part in message.get("parts", []) if part.get("type") != "reasoning"],
            }
        )
    return copied


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8") as source:
        exported = visible_export(json.load(source))

    session = exported["info"]
    session_time = session.get("time", {})
    session_model = session.get("model", {})
    session_tokens = session.get("tokens", {})
    session_cache = session_tokens.get("cache", {})
    exported_at_ms = int(__import__("time").time() * 1000)
    rows = []
    event_index = 0
    for message in exported.get("messages", []):
        info = message.get("info", {})
        parts = message.get("parts", [])
        message_time = info.get("time", {})
        for part in parts:
            state = part.get("state", {}) if part.get("type") == "tool" else {}
            rows.append(
                {
                "session_id": session.get("id"),
                "session_title": session.get("title"),
                "session_created_ms": integer(session_time.get("created")),
                "session_updated_ms": integer(session_time.get("updated")),
                "session_agent": session.get("agent"),
                "session_provider_id": session_model.get("providerID"),
                "session_model_id": session_model.get("id"),
                "session_model_variant": session_model.get("variant"),
                "session_cost": number(session.get("cost")),
                "session_tokens_input": integer(session_tokens.get("input")),
                "session_tokens_output": integer(session_tokens.get("output")),
                "session_tokens_reasoning": integer(session_tokens.get("reasoning")),
                "session_tokens_cache_read": integer(session_cache.get("read")),
                "session_tokens_cache_write": integer(session_cache.get("write")),
                "exported_at_ms": exported_at_ms,
                "message_id": info.get("id"),
                "event_id": part.get("id") or f"{info.get('id')}:{event_index}",
                "event_index": event_index,
                "event_type": part.get("type"),
                "role": info.get("role"),
                "message_created_ms": integer(message_time.get("created")),
                "message_completed_ms": integer(message_time.get("completed")),
                "agent": info.get("agent"),
                "provider_id": info.get("providerID"),
                "model_id": info.get("modelID"),
                "content": part.get("text") if isinstance(part.get("text"), str) else None,
                "tool_name": part.get("tool"),
                "tool_title": state.get("title"),
                "tool_status": state.get("status"),
                "tool_input_json": json_value(state.get("input")),
                "tool_output": state.get("output") if isinstance(state.get("output"), str) else json_value(state.get("output")),
                "details_json": json_value(part),
                }
            )
            event_index += 1

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), args.output, compression="zstd")


if __name__ == "__main__":
    main()
