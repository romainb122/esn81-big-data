#!/usr/bin/env python3
"""Consume Redpanda events into the append-only Iceberg Bronze table."""

import json
import os

import pyarrow as pa
from kafka import KafkaConsumer
from pyiceberg.exceptions import NoSuchNamespaceError, NoSuchTableError

from iceberg_catalog import catalog
from opencode_event_schema import SCHEMA, iceberg_schema


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
            # Commit only after Iceberg has committed its new snapshot.
            consumer.commit()
            print(f"Appended {len(rows)} event(s) to opencode.events_bronze", flush=True)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
