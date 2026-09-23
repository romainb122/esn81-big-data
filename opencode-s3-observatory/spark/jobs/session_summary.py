#!/usr/bin/env python3
"""Build transactional OpenCode summaries from the Iceberg events table."""

import argparse
import os

from pyspark.sql import SparkSession, functions as F


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-table",
        default=os.environ.get("SPARK_INPUT_TABLE", "opencode.opencode.events"),
    )
    parser.add_argument(
        "--sessions-table",
        default=os.environ.get("SPARK_SESSIONS_TABLE", "opencode.opencode.session_summary"),
    )
    parser.add_argument(
        "--tools-table",
        default=os.environ.get("SPARK_TOOLS_TABLE", "opencode.opencode.tool_summary"),
    )
    args = parser.parse_args()

    spark = SparkSession.builder.appName("opencode-session-summary").getOrCreate()
    events = spark.table(args.input_table)

    sessions = events.groupBy("session_id").agg(
        F.max("session_title").alias("session_title"),
        F.max("session_updated_ms").alias("session_updated_ms"),
        F.max("session_agent").alias("session_agent"),
        F.max("session_provider_id").alias("session_provider_id"),
        F.max("session_model_id").alias("session_model_id"),
        F.max("session_cost").alias("session_cost"),
        F.max("session_tokens_input").alias("tokens_input"),
        F.max("session_tokens_output").alias("tokens_output"),
        F.max("session_tokens_reasoning").alias("tokens_reasoning"),
        F.max("session_tokens_cache_read").alias("tokens_cache_read"),
        F.max("session_tokens_cache_write").alias("tokens_cache_write"),
        F.count("*").alias("event_count"),
        F.countDistinct("message_id").alias("message_count"),
        F.sum(F.when(F.col("event_type") == "tool", 1).otherwise(0)).alias("tool_call_count"),
    )
    sessions.writeTo(args.sessions_table).using("iceberg").createOrReplace()

    tools = (
        events.filter(F.col("tool_name").isNotNull())
        .groupBy("session_id", "tool_name", "tool_status")
        .agg(F.count("*").alias("call_count"))
    )
    tools.writeTo(args.tools_table).using("iceberg").createOrReplace()

    spark.stop()


if __name__ == "__main__":
    main()
