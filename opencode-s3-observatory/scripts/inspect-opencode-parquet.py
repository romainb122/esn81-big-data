#!/usr/bin/env python3
"""Print a small, readable sample from an OpenCode Parquet export."""

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    columns = [
        "session_id",
        "message_id",
        "role",
        "message_created_ms",
        "agent",
        "provider_id",
        "model_id",
        "text",
    ]
    table = pq.read_table(args.file, columns=columns)
    print(json.dumps(table.slice(0, args.limit).to_pylist(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
