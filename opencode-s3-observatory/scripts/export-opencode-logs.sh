#!/usr/bin/env bash
set -euo pipefail

endpoint="${S3_ENDPOINT:-http://localhost:8333}"
bucket="${S3_BUCKET:-bigdata}"
access_key="${AWS_ACCESS_KEY_ID:-admin}"
secret_key="${AWS_SECRET_ACCESS_KEY:-bigdata-local-secret}"
region="${AWS_REGION:-us-east-1}"
prefix="${S3_PREFIX:-opencode-logs}"
max_sessions="${OPENCODE_LOG_MAX_SESSIONS:-100}"
include_diagnostic_log=false

usage() {
    cat <<'EOF'
Usage: ./export-opencode-logs.sh [--max-sessions N] [--include-diagnostic-log]

Exports recent OpenCode sessions with sensitive data redacted, archives them,
and uploads the archive to the configured S3 bucket.

Environment variables: S3_ENDPOINT, S3_BUCKET, AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_PREFIX, OPENCODE_LOG_MAX_SESSIONS.
EOF
}

while (($# > 0)); do
    case "$1" in
        --max-sessions)
            max_sessions="${2:?--max-sessions requires a value}"
            shift 2
            ;;
        --include-diagnostic-log)
            include_diagnostic_log=true
            shift
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

for command in opencode curl python3 tar; do
    command -v "$command" >/dev/null || {
        printf 'Required command not found: %s\n' "$command" >&2
        exit 1
    }
done

case "$max_sessions" in
    ''|*[!0-9]*)
        printf '%s\n' '--max-sessions must be a positive integer.' >&2
        exit 2
        ;;
esac

work_dir="$(mktemp -d)"
archive_path="$(mktemp --suffix=.tar.gz)"
cleanup() {
    rm -rf "$work_dir" "$archive_path"
}
trap cleanup EXIT

mkdir -p "$work_dir/sessions"
opencode session list --format json --max-count "$max_sessions" > "$work_dir/sessions.json"
python3 -c '
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    for session in json.load(source):
        print(session["id"])
' "$work_dir/sessions.json" > "$work_dir/session-ids.txt"

while IFS= read -r session_id; do
    [ -n "$session_id" ] || continue
    opencode export "$session_id" --sanitize > "$work_dir/sessions/$session_id.json"
done < "$work_dir/session-ids.txt"

if "$include_diagnostic_log"; then
    data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/opencode"
    if [ -f "$data_dir/log/opencode.log" ]; then
        cp "$data_dir/log/opencode.log" "$work_dir/opencode.log"
    else
        printf 'Diagnostic log not found at %s; continuing without it.\n' "$data_dir/log/opencode.log" >&2
    fi
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive_name="opencode-${timestamp}.tar.gz"
object_key="${prefix%/}/${timestamp}/${archive_name}"
tar -C "$work_dir" -czf "$archive_path" .

curl --fail-with-body --silent --show-error \
    --aws-sigv4 "aws:amz:${region}:s3" \
    --user "${access_key}:${secret_key}" \
    --upload-file "$archive_path" \
    "${endpoint%/}/${bucket}/${object_key}"

printf 'Uploaded sanitized OpenCode exports to s3://%s/%s\n' "$bucket" "$object_key"
