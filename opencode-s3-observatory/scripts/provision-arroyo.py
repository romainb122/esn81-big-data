#!/usr/bin/env python3
"""Create the live Arroyo pipeline once; safe to run after every compose up."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("ARROYO_API", "http://arroyo:5115/api/v1")
NAME = "conversation-observatory-live"
QUERY = Path(os.environ.get("ARROYO_QUERY", "/config/arroyo-live.sql")).read_text()


def request(path, body=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=payload,
        headers={"Content-Type": "application/json"} if payload else {},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.loads(response.read())


for attempt in range(60):
    try:
        pipelines = request("/pipelines?limit=100").get("data", [])
        existing = next((pipeline for pipeline in pipelines if pipeline.get("name") == NAME), None)
        if existing:
            print(f"Arroyo pipeline already exists: {existing['id']}")
            raise SystemExit(0)
        validation = request("/pipelines/validate_query", {"query": QUERY, "udfs": []})
        if validation.get("errors"):
            raise RuntimeError("; ".join(validation["errors"]))
        pipeline = request("/pipelines", {"name": NAME, "parallelism": 1, "query": QUERY, "udfs": []})
        print(f"Created Arroyo pipeline: {pipeline['id']}")
        raise SystemExit(0)
    except (urllib.error.URLError, ConnectionError) as error:
        if attempt == 59:
            raise
        print(f"Waiting for Arroyo ({error})", flush=True)
        time.sleep(2)
