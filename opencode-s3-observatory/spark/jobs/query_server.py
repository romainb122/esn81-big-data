#!/usr/bin/env python3
"""Expose a local, read-only Spark SQL endpoint for the dashboard."""

import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

from pyspark.sql import SparkSession


# Spark identifiers are catalog.namespace.table. The Iceberg catalog and the
# namespace are both named "opencode" in this local deployment.
EVENTS_TABLE = os.environ.get("SPARK_EVENTS_TABLE", "opencode.opencode.events")
MAX_RESULT_ROWS = 500
READ_QUERY = re.compile(r"^\s*(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", re.IGNORECASE)
TABLE_ALIASES = (
    ("opencode.events", "events"),
    ("opencode.session_summary", "opencode.opencode.session_summary"),
    ("opencode.tool_summary", "opencode.opencode.tool_summary"),
)


def translate_sql(statement):
    """Map the public Iceberg names to Spark catalog identifiers."""
    translated = statement.strip().rstrip(";")
    for source, target in TABLE_ALIASES:
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated, flags=re.IGNORECASE)
    return translated


def json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


spark = SparkSession.builder.appName("opencode-sql-gateway").getOrCreate()
spark_query_lock = Lock()


def refresh_views():
    # Spark resolves one Iceberg snapshot for each query instead of scanning the
    # mutable landing files directly.
    spark.table(EVENTS_TABLE).createOrReplaceTempView("events")


class QueryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            try:
                self.wfile.write(b"ok\n")
            except BrokenPipeError:
                pass
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/query":
            self.send_error(404)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length))
            statement = translate_sql(str(payload.get("sql", "")))
            if ";" in statement or not READ_QUERY.match(statement):
                raise ValueError("Seules les requetes SELECT, WITH, SHOW, DESCRIBE et EXPLAIN sont autorisees.")
            # Spark queries share one local session, so keep query execution
            # serial while allowing health checks to return immediately.
            with spark_query_lock:
                refresh_views()
                result = spark.sql(statement).limit(MAX_RESULT_ROWS)
                rows = [{key: json_value(value) for key, value in row.asDict(recursive=True).items()} for row in result.collect()]
            self.send_json(200, {"sql": statement, "columns": result.columns, "rows": rows, "max_rows": MAX_RESULT_ROWS})
        except Exception as error:
            self.send_json(400, {"error": str(error)})

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, default=json_value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 4041), QueryHandler).serve_forever()
