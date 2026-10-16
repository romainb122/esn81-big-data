#!/usr/bin/env python3
"""Run one prompt through configured command adapters and emit JSONL results.

Each adapter receives the prompt through stdin unless its command contains the
literal ``{prompt}``. The command may return JSON with response/metric fields;
otherwise stdout is kept as the response and only duration is recorded.
"""

import argparse
import json
import subprocess
import time
import uuid
from pathlib import Path


def extract_jsonl(output):
    events = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    if not events:
        try:
            value = json.loads(output)
            return value if isinstance(value, dict) else {"response": output}
        except json.JSONDecodeError:
            return {"response": output}

    payload = {}
    text_parts = []
    errors = []

    def visit(value, role=None):
        if isinstance(value, dict):
            current_role = value.get("role", role)
            if isinstance(value.get("usage"), dict):
                payload.update(value["usage"])
            if isinstance(value.get("tokens"), dict):
                payload.update(value["tokens"])
            if isinstance(value.get("cost"), (int, float)):
                payload["cost"] = value["cost"]
            if isinstance(value.get("model"), str):
                payload["model"] = value["model"]
            if isinstance(value.get("provider"), str):
                payload["provider"] = value["provider"]
            if isinstance(value.get("error"), str):
                errors.append(value["error"])
            elif isinstance(value.get("error"), dict):
                errors.append(value["error"].get("message") or json.dumps(value["error"]))
            if current_role not in {"user", "system"}:
                for key in ("text", "output_text"):
                    if isinstance(value.get(key), str):
                        text_parts.append(value[key])
                content = value.get("content")
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            visit(part, current_role)
            for nested_key in ("message", "item", "response", "part"):
                if isinstance(value.get(nested_key), dict):
                    visit(value[nested_key], current_role)
        elif isinstance(value, list):
            for item in value:
                visit(item, role)

    for event in events:
        visit(event)
    if text_parts:
        payload["response"] = "".join(dict.fromkeys(text_parts))
    if errors:
        payload["error"] = "\n".join(dict.fromkeys(errors))
    return payload


def run(adapter, prompt, comparison_id):
    command = [part.replace("{prompt}", prompt) for part in adapter["command"]]
    uses_prompt = any("{prompt}" in part for part in adapter["command"])
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        input=None if uses_prompt else prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    payload = extract_jsonl(completed.stdout.strip())
    result = {
        "comparison_id": comparison_id,
        "prompt": prompt,
        "harness": adapter.get("harness"),
        "provider": payload.get("provider", adapter.get("provider")),
        "model": payload.get("model", adapter.get("model")),
        "duration_ms": duration_ms,
        "temperature": adapter.get("temperature"),
        "context_window": adapter.get("context_window"),
        "input_tokens": payload.get("input_tokens", payload.get("input")),
        "output_tokens": payload.get("output_tokens", payload.get("output")),
        "total_tokens": payload.get("total_tokens", payload.get("totalTokens", payload.get("total"))),
        "cost": payload.get("cost", {}).get("total") if isinstance(payload.get("cost"), dict) else payload.get("cost"),
        "context_used": payload.get("context_used"),
        "response": payload.get("response"),
        "status": "error" if completed.returncode != 0 or payload.get("error") else "ok",
        "error": payload.get("error") or completed.stderr.strip() or None,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--config", type=Path, required=True, help="JSON file containing an adapters array")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    comparison_id = str(uuid.uuid4())
    rows = [run(adapter, args.prompt, comparison_id) for adapter in config["adapters"]]
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(f"Wrote {len(rows)} comparison result(s) to {args.output}")


if __name__ == "__main__":
    main()
