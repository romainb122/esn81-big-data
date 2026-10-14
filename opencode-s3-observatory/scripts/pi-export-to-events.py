#!/usr/bin/env python3
"""Convert a pi JSONL session into the Observatory visible-event contract.

Pi stores one JSON object per line.  Thinking blocks are deliberately ignored;
text, tool calls and tool results are retained so the existing Redpanda/
Iceberg/Spark pipeline can consume the result unchanged.
"""

import argparse
import json
import time
from pathlib import Path


def text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(item.get("text", "") for item in value if isinstance(item, dict))
    return None


def json_value(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value is not None else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--events-output", type=Path, required=True)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    header = next(record for record in records if record.get("type") == "session")
    session_id = header["id"]
    session_timestamp = header.get("timestamp")
    session_created_ms = int(session_timestamp) if isinstance(session_timestamp, (int, float)) else None
    exported_at_ms = int(time.time() * 1000)
    messages = [record for record in records if record.get("type") == "message"]
    model = next((record["message"].get("model") for record in reversed(messages)
                  if record.get("message", {}).get("model")), None)
    rows = []
    event_index = 0

    for record in messages:
        message = record.get("message", {})
        role = message.get("role")
        if role in {"system", "toolResult"}:
            # System prompts and tool results are handled below only for the
            # latter.  System instructions are not conversation-visible data.
            if role == "system":
                continue
        message_id = record.get("id")
        timestamp = message.get("timestamp") or record.get("timestamp")
        timestamp_ms = int(timestamp) if isinstance(timestamp, (int, float)) else None
        usage = message.get("usage", {})
        cost = (usage.get("cost") or {}).get("total") if isinstance(usage.get("cost"), dict) else None

        if role == "toolResult":
            content = text(message.get("content"))
            rows.append({
                "session_id": session_id, "session_title": Path(args.input).stem,
                "session_created_ms": session_created_ms, "session_updated_ms": timestamp_ms,
                "session_agent": "pi", "session_provider_id": message.get("provider"),
                "session_model_id": model, "session_model_variant": None,
                "session_cost": cost, "session_tokens_input": None, "session_tokens_output": None,
                "session_tokens_reasoning": None, "session_tokens_cache_read": None,
                "session_tokens_cache_write": None, "exported_at_ms": exported_at_ms,
                "message_id": message.get("toolCallId") or message_id,
                "event_id": message_id or f"tool-result:{event_index}", "event_index": event_index,
                "event_type": "tool", "role": "tool", "message_created_ms": timestamp_ms,
                "message_completed_ms": timestamp_ms, "agent": "pi", "provider_id": message.get("provider"),
                "model_id": model, "content": None, "tool_name": message.get("toolName"),
                "tool_title": message.get("toolName"), "tool_status": "error" if message.get("isError") else "success",
                "tool_input_json": None, "tool_output": content, "details_json": json_value({"durationMs": message.get("durationMs")}),
            })
            event_index += 1
            continue

        for part in message.get("content", []):
            part_type = part.get("type") if isinstance(part, dict) else None
            if part_type == "thinking":
                continue
            tool_call = part_type == "toolCall"
            rows.append({
                "session_id": session_id, "session_title": Path(args.input).stem,
                "session_created_ms": session_created_ms, "session_updated_ms": timestamp_ms,
                "session_agent": "pi", "session_provider_id": message.get("provider"),
                "session_model_id": message.get("model") or model, "session_model_variant": None,
                "session_cost": cost, "session_tokens_input": usage.get("input"),
                "session_tokens_output": usage.get("output"), "session_tokens_reasoning": None,
                "session_tokens_cache_read": usage.get("cacheRead"), "session_tokens_cache_write": usage.get("cacheWrite"),
                "exported_at_ms": exported_at_ms, "message_id": message_id,
                "event_id": part.get("id") or f"{message_id}:{event_index}", "event_index": event_index,
                "event_type": "tool" if tool_call else "text", "role": role,
                "message_created_ms": timestamp_ms, "message_completed_ms": timestamp_ms,
                "agent": "pi", "provider_id": message.get("provider"), "model_id": message.get("model") or model,
                "content": None if tool_call else part.get("text"),
                "tool_name": part.get("name") if tool_call else None,
                "tool_title": part.get("name") if tool_call else None,
                "tool_status": "pending" if tool_call else None,
                "tool_input_json": json_value(part.get("arguments")) if tool_call else None,
                "tool_output": None, "details_json": json_value({"stopReason": message.get("stopReason")}),
            })
            event_index += 1

    args.events_output.parent.mkdir(parents=True, exist_ok=True)
    args.events_output.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
