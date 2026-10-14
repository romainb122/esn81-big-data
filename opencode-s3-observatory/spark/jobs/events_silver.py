#!/usr/bin/env python3
"""Promote the latest Bronze snapshot of each pi session into Silver."""

import argparse
import os

from pyspark.sql import SparkSession, functions as F


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-table",
        default=os.environ.get("SPARK_BRONZE_TABLE", "opencode.opencode.events_bronze"),
    )
    parser.add_argument(
        "--output-table",
        default=os.environ.get("SPARK_SILVER_TABLE", "opencode.opencode.events"),
    )
    args = parser.parse_args()

    spark = SparkSession.builder.appName("opencode-events-silver").getOrCreate()
    bronze = spark.table(args.input_table)
    latest_exports = bronze.groupBy("session_id").agg(F.max("exported_at_ms").alias("exported_at_ms"))
    latest_events = (
        bronze.join(latest_exports, ["session_id", "exported_at_ms"])
        .dropDuplicates(["session_id", "event_id"])
    )

    if spark.catalog.tableExists(args.output_table):
        unchanged_events = spark.table(args.output_table).join(
            latest_events.select("session_id").distinct(), "session_id", "left_anti"
        )
        latest_events = unchanged_events.unionByName(latest_events)

    # Replacing the table creates one Iceberg snapshot, so readers never observe
    # a state where refreshed sessions were deleted but not yet reinserted.
    latest_events.writeTo(args.output_table).using("iceberg").createOrReplace()
    spark.stop()


if __name__ == "__main__":
    main()
