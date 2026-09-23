#!/usr/bin/env bash
set -euo pipefail

endpoint="${S3_ENDPOINT:-http://localhost:8333}"
bucket="${S3_BUCKET:-bigdata}"
access_key="${AWS_ACCESS_KEY_ID:-admin}"
secret_key="${AWS_SECRET_ACCESS_KEY:-bigdata-local-secret}"
region="${AWS_REGION:-us-east-1}"
prefix="${S3_PREFIX:-opencode-observatory}"
max_sessions="${OPENCODE_EXPORT_MAX_SESSIONS:-100}"
force=false
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/opencode-s3-export"
state_file="$state_dir/session-updates.json"
python_bin="${OPENCODE_EXPORT_PYTHON:-$project_dir/.venv/bin/python}"

usage() {
    cat <<'EOF'
Usage: ./export-opencode-conversations.sh [--force] [--max-sessions N]

Exports each changed OpenCode session as sanitized JSON and Parquet to S3.
EOF
}

while (($# > 0)); do
    case "$1" in
        --force)
            force=true
            shift
            ;;
        --max-sessions)
            max_sessions="${2:?--max-sessions requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
done

for command in opencode curl flock; do
    command -v "$command" >/dev/null || {
        printf 'Required command not found: %s\n' "$command" >&2
        exit 1
    }
done
[ -x "$python_bin" ] || {
    printf '%s\n' "Python environment not found: $python_bin. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements-opencode-export.txt" >&2
    exit 1
}
"$python_bin" -c 'import pyarrow' >/dev/null 2>&1 || {
    printf '%s\n' 'PyArrow is required. Run: .venv/bin/pip install -r requirements-opencode-export.txt' >&2
    exit 1
}

case "$max_sessions" in
    ''|*[!0-9]*)
        printf '%s\n' '--max-sessions must be a positive integer.' >&2
        exit 2
        ;;
esac

mkdir -p "$state_dir"
exec 9>"$state_dir/export.lock"
if ! flock -n 9; then
    printf '%s\n' 'An OpenCode export is already running; skipping this run.'
    exit 0
fi

work_dir="$(mktemp -d)"
cleanup() {
    rm -rf "$work_dir"
}
trap cleanup EXIT

sessions_file="$work_dir/sessions.json"
changed_ids_file="$work_dir/changed-session-ids.txt"
opencode session list --format json --max-count "$max_sessions" > "$sessions_file"
"$python_bin" - "$sessions_file" "$state_file" "$force" > "$changed_ids_file" <<'PY'
import json
import sys
from pathlib import Path

sessions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
state_path = Path(sys.argv[2])
force = sys.argv[3] == "true"
try:
    exported = json.loads(state_path.read_text(encoding="utf-8"))
except FileNotFoundError:
    exported = {}

for session in sessions:
    session_id = session["id"]
    if force or exported.get(session_id) != session.get("updated"):
        print(session_id)
PY

if [ ! -s "$changed_ids_file" ]; then
    printf '%s\n' 'No changed OpenCode sessions to export.'
    exit 0
fi

upload() {
    local file="$1"
    local key="$2"
    curl --fail-with-body --silent --show-error \
        --aws-sigv4 "aws:amz:${region}:s3" \
        --user "${access_key}:${secret_key}" \
        --upload-file "$file" \
        "${endpoint%/}/${bucket}/${key}"
}

while IFS= read -r session_id; do
    [ -n "$session_id" ] || continue
    json_file="$work_dir/$session_id.json"
    parquet_file="$work_dir/$session_id.parquet"
    raw_file="$work_dir/$session_id.raw.json"
    visible_json_file="$work_dir/$session_id.json"
    opencode export "$session_id" > "$raw_file"
    "$python_bin" "$project_dir/scripts/opencode-export-to-parquet.py" "$raw_file" "$parquet_file" --json-output "$visible_json_file"
    upload "$visible_json_file" "${prefix%/}/sessions/$session_id.json"
    upload "$parquet_file" "${prefix%/}/parquet/sessions/$session_id.parquet"
    "$python_bin" "$project_dir/scripts/sync-opencode-iceberg.py" "$parquet_file"
    printf 'Exported %s\n' "$session_id"
done < "$changed_ids_file"

"$python_bin" - "$sessions_file" "$state_file" <<'PY'
import json
import os
import sys
from pathlib import Path

sessions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
state_path = Path(sys.argv[2])
updated = {session["id"]: session.get("updated") for session in sessions}
temporary = state_path.with_suffix(".tmp")
temporary.write_text(json.dumps(updated, sort_keys=True), encoding="utf-8")
os.replace(temporary, state_path)
PY
