#!/usr/bin/env python3
"""Append normalized technical comparison runs to Iceberg.

Input is JSONL, one run per line. Unknown fields are ignored and unavailable
metrics remain null; this command never fabricates provider data.
"""

import argparse
import json
import time
from pathlib import Path

import pyarrow as pa
from pyiceberg.exceptions import NoSuchNamespaceError, NoSuchTableError
from pyiceberg.types import StringType

from comparison_schema import COMPARISON_SCHEMA, iceberg_schema
from iceberg_catalog import catalog

TABLE_NAME = "opencode.comparison_runs"


def table():
    iceberg = catalog()
    try:
        iceberg.create_namespace("opencode")
    except NoSuchNamespaceError:
        pass
    except Exception as error:
        if "already exists" not in str(error).lower():
            raise
    try:
        loaded = iceberg.load_table(TABLE_NAME)
        existing = {field.name for field in loaded.schema().fields}
        missing = [field.name for field in COMPARISON_SCHEMA if field.name not in existing]
        if missing:
            update = loaded.update_schema()
            for name in missing:
                update.add_column(name, StringType())
            update.commit()
            loaded = iceberg.load_table(TABLE_NAME)
        return loaded
    except NoSuchTableError:
        return iceberg.create_table(TABLE_NAME, schema=iceberg_schema())


def integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def normalize(item):
    return {
        "comparison_id": item.get("comparison_id"),
        "prompt": item.get("prompt"),
        "harness": item.get("harness"),
        "provider": item.get("provider"),
        "model": item.get("model"),
        "input_tokens": integer(item.get("input_tokens")),
        "output_tokens": integer(item.get("output_tokens")),
        "total_tokens": integer(item.get("total_tokens")),
        "cost": number(item.get("cost")),
        "duration_ms": integer(item.get("duration_ms")),
        "temperature": number(item.get("temperature")),
        "context_window": integer(item.get("context_window")),
        "context_used": integer(item.get("context_used")),
        "created_at_ms": integer(item.get("created_at_ms")) or int(time.time() * 1000),
        "status": item.get("status"),
        "response": item.get("response"),
        "error": item.get("error"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSONL file containing comparison runs")
    args = parser.parse_args()
    rows = [normalize(json.loads(line)) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("No comparison runs found")
    table().append(pa.Table.from_pylist(rows, schema=COMPARISON_SCHEMA))
    print(f"Appended {len(rows)} comparison run(s) to {TABLE_NAME}")


if __name__ == "__main__":
    main()
