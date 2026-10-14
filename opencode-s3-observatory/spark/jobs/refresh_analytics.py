#!/usr/bin/env python3
"""Run the Silver promotion before rebuilding the dependent Gold tables."""

import runpy
from pathlib import Path


JOB_DIRECTORY = Path(__file__).parent

runpy.run_path(JOB_DIRECTORY / "events_silver.py", run_name="__main__")
runpy.run_path(JOB_DIRECTORY / "session_summary.py", run_name="__main__")
