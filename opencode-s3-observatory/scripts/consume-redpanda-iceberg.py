#!/usr/bin/env python3
"""Consume Redpanda events into the append-only Iceberg Bronze table."""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pyarrow as pa
from kafka import KafkaConsumer
from pyiceberg.exceptions import NoSuchNamespaceError, NoSuchTableError

from iceberg_catalog import catalog
from opencode_event_schema import SCHEMA, iceberg_schema


_commit_condition = threading.Condition()
_commit_version = 0


def announce_commit():
    global _commit_version
    with _commit_condition:
        _commit_version = int(time.time() * 1000)
        _commit_condition.notify_all()


class CommitEvents(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/events":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        seen = _commit_version
        try:
            self.wfile.write(b"retry: 2000\n\n")
            self.wfile.flush()
            while True:
                with _commit_condition:
                    _commit_condition.wait_for(lambda: _commit_version != seen, timeout=15)
                    current = _commit_version
                if current != seen:
                    seen = current
                    self.wfile.write(f"event: bronze-commit\ndata: {current}\n\n".encode())
                else:
                    self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_args):
        pass


def start_commit_server():
    server = ThreadingHTTPServer(("0.0.0.0", 4042), CommitEvents)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def bronze_table():
    iceberg = catalog()
    try:
        iceberg.create_namespace("opencode")
    except NoSuchNamespaceError:
        pass
    except Exception as error:
        if "already exists" not in str(error).lower():
            raise
    try:
        return iceberg.load_table("opencode.events_bronze")
    except NoSuchTableError:
        return iceberg.create_table("opencode.events_bronze", schema=iceberg_schema())


def main():
    start_commit_server()
    topic = os.environ.get("REDPANDA_TOPIC", "opencode.events")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=os.environ.get("REDPANDA_BROKERS", "redpanda:9092"),
        group_id=os.environ.get("REDPANDA_CONSUMER_GROUP", "opencode-iceberg-bronze"),
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    table = bronze_table()
    try:
        while True:
            records = consumer.poll(timeout_ms=1000, max_records=100)
            rows = [record.value for partition in records.values() for record in partition]
            if not rows:
                continue
            table.append(pa.Table.from_pylist(rows, schema=SCHEMA))
            # Commit and notify browsers only after Iceberg made the snapshot visible.
            consumer.commit()
            finalized_response = any(
                row.get("role") == "assistant"
                and (row.get("message_completed_ms") is not None or row.get("session_tokens_output") is not None)
                for row in rows
            )
            if finalized_response:
                announce_commit()
            print(f"Appended {len(rows)} event(s) to opencode.events_bronze", flush=True)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
