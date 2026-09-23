#!/usr/bin/env python3
"""Append one OpenCode Parquet export to the Iceberg events table."""

import argparse
import os

import pyarrow as pa
import pyarrow.parquet as pq
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchNamespaceError, NoSuchTableError
from pyiceberg.schema import Schema
from pyiceberg.types import DoubleType, LongType, NestedField, StringType


def catalog():
    return load_catalog(
        "opencode",
        type="rest",
        uri=os.environ.get("ICEBERG_URI", "http://localhost:8181"),
        warehouse=f"s3://{os.environ.get('S3_BUCKET', 'bigdata')}/iceberg/",
        **{
            "s3.endpoint": os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
            "s3.access-key-id": os.environ.get("AWS_ACCESS_KEY_ID", "admin"),
            "s3.secret-access-key": os.environ.get("AWS_SECRET_ACCESS_KEY", "bigdata-local-secret"),
            "s3.region": os.environ.get("AWS_REGION", "us-east-1"),
            "s3.path-style-access": "true",
        },
    )


def iceberg_schema(events):
    fields = []
    for field_id, field in enumerate(events.schema, start=1):
        if pa.types.is_int64(field.type):
            field_type = LongType()
        elif pa.types.is_float64(field.type):
            field_type = DoubleType()
        else:
            field_type = StringType()
        fields.append(NestedField(field_id=field_id, name=field.name, field_type=field_type, required=False))
    return Schema(*fields)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("parquet_file")
    args = parser.parse_args()

    events = pq.read_table(args.parquet_file)
    iceberg = catalog()
    try:
        iceberg.create_namespace("opencode")
    except NoSuchNamespaceError:
        pass
    except Exception as error:
        if "already exists" not in str(error).lower():
            raise

    try:
        table = iceberg.load_table("opencode.events")
    except NoSuchTableError:
        table = iceberg.create_table("opencode.events", schema=iceberg_schema(events))
    session_id = events.column("session_id")[0].as_py()
    # Keep one current copy per session in the active snapshot. Iceberg retains
    # the prior snapshots, while the dashboard avoids scanning duplicate events.
    table.overwrite(events, overwrite_filter=f"session_id = '{session_id}'")


if __name__ == "__main__":
    main()
