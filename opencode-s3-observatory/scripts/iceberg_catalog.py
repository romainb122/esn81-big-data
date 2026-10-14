"""Iceberg REST catalog configuration shared by local ingestion tools."""

import os

from pyiceberg.catalog import load_catalog


def catalog():
    return load_catalog(
        "opencode",
        type="rest",
        uri=os.environ.get("ICEBERG_URI", "http://iceberg:8181"),
        warehouse=f"s3://{os.environ.get('S3_BUCKET', 'bigdata')}/iceberg/",
        **{
            "s3.endpoint": os.environ.get("S3_ENDPOINT", "http://s3:8333"),
            "s3.access-key-id": os.environ.get("AWS_ACCESS_KEY_ID", "admin"),
            "s3.secret-access-key": os.environ.get("AWS_SECRET_ACCESS_KEY", "bigdata-local-secret"),
            "s3.region": os.environ.get("AWS_REGION", "us-east-1"),
            "s3.path-style-access": "true",
        },
    )
