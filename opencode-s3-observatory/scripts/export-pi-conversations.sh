#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
redpanda_proxy_url="${REDPANDA_PROXY_URL:-http://localhost:18082}"
redpanda_topic="${REDPANDA_TOPIC:-opencode.events}"
python_bin="${PI_EXPORT_PYTHON:-python3}"
session_root="${PI_SESSION_ROOT:-${HOME}/.pi/agent/sessions}"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/pi-s3-export"
state_file="$state_dir/session-mtimes.json"
max_sessions="${PI_EXPORT_MAX_SESSIONS:-100}"

command -v flock >/dev/null || { echo "Required command not found: flock" >&2; exit 1; }
command -v "$python_bin" >/dev/null || { echo "Required command not found: $python_bin" >&2; exit 1; }
mkdir -p "$state_dir"
exec 9>"$state_dir/export.lock"
flock -n 9 || { echo 'A pi export is already running; skipping this run.'; exit 0; }

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
exported_ids="$work_dir/exported.txt"

"$python_bin" - "$session_root" "$state_file" "$max_sessions" > "$exported_ids" <<'PY'
import json, sys
from pathlib import Path
root, state_path, limit = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
try: state = json.loads(state_path.read_text(encoding='utf-8'))
except FileNotFoundError: state = {}
files = sorted(root.rglob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
for path in files:
    key = str(path)
    mtime = path.stat().st_mtime_ns
    if state.get(key) != mtime:
        print(f'{mtime}\t{path}')
PY

while IFS=$'\t' read -r mtime session_file; do
    [ -n "${session_file:-}" ] || continue
    events_file="$work_dir/$(basename "$session_file").events.jsonl"
    "$python_bin" "$project_dir/scripts/pi-export-to-events.py" "$session_file" --events-output "$events_file"
    "$python_bin" "$project_dir/scripts/publish-events.py" "$events_file" --url "$redpanda_proxy_url" --topic "$redpanda_topic"
done < "$exported_ids"

"$python_bin" - "$session_root" "$state_file" "$max_sessions" <<'PY'
import json, os, sys
from pathlib import Path
root, state_path, limit = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
files = sorted(root.rglob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
state = {str(p): p.stat().st_mtime_ns for p in files}
tmp = state_path.with_suffix('.tmp')
tmp.write_text(json.dumps(state, sort_keys=True), encoding='utf-8')
os.replace(tmp, state_path)
PY
