#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prompt="${*:?Usage: ./scripts/run-technical-comparison.sh 'prompt'}"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

python3 "$project_dir/scripts/run-comparison.py" "$prompt" \
  --config "$project_dir/config/comparison-adapters.json" \
  --output "$work_dir/runs.jsonl"

cd "$project_dir"
docker compose run --rm --no-deps \
  -v "$work_dir":/workspace \
  iceberg-sink \
  python /app/scripts/record-comparison.py /workspace/runs.jsonl

echo "Comparaison terminée. Ouvrir http://localhost:8501 puis Comparateur technique."
