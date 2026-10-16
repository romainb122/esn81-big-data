#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
agent_dir="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
extension_dir="$agent_dir/extensions"
target="$extension_dir/conversation-observatory.ts"
source="$project_dir/pi/extensions/observatory-export.ts"

mkdir -p "$extension_dir"
ln -sfn "$source" "$target"
printf 'Extension installee : %s\n' "$target"
printf 'Redemarre Pi ou execute /reload dans une session existante.\n'
