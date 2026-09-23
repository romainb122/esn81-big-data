#!/usr/bin/env python3
"""Remove duplicate current rows before re-exporting OpenCode sessions."""

from pathlib import Path
from runpy import run_path

catalog = run_path(Path(__file__).with_name("sync-opencode-iceberg.py"))["catalog"]


def main():
    table = catalog().load_table("opencode.events")
    table.delete("session_id IS NOT NULL")
    print("Current Iceberg snapshot cleared. Run the forced OpenCode export next.")


if __name__ == "__main__":
    main()
