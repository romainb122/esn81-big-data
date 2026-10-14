#!/usr/bin/env python3
"""Publish conversation event records to the Redpanda REST Proxy."""

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def batches(values, size):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("events_file", type=Path)
    parser.add_argument("--topic", default=os.environ.get("REDPANDA_TOPIC", "opencode.events"))
    parser.add_argument("--url", default=os.environ.get("REDPANDA_PROXY_URL", "http://localhost:18082"))
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.events_file.read_text(encoding="utf-8").splitlines() if line]
    for batch in batches(records, args.batch_size):
        payload = {
            "records": [
                {
                    "key": f"{record['session_id']}:{record['event_id']}",
                    "value": record,
                }
                for record in batch
            ]
        }
        request = Request(
            f"{args.url.rstrip('/')}/topics/{args.topic}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "application/vnd.kafka.v2+json",
                "Content-Type": "application/vnd.kafka.json.v2+json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status not in range(200, 300):
                    raise RuntimeError(f"Redpanda REST Proxy returned HTTP {response.status}")
        except HTTPError as error:
            raise RuntimeError(error.read().decode("utf-8", errors="replace")) from error
        except URLError as error:
            raise RuntimeError(f"Redpanda REST Proxy unavailable: {error.reason}") from error

    print(f"Published {len(records)} event(s) to {args.topic}")


if __name__ == "__main__":
    main()
