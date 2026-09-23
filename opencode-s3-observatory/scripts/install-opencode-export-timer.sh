#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
service_name="opencode-s3-export.service"
timer_name="opencode-s3-export.timer"
opencode_dir="$(dirname "$(command -v opencode)")"

mkdir -p "$unit_dir"
cat > "$unit_dir/$service_name" <<EOF
[Unit]
Description=Export visible OpenCode events to local S3 and Apache Iceberg

[Service]
Type=oneshot
WorkingDirectory=$project_dir
Environment=PATH=$opencode_dir:/usr/local/bin:/usr/bin:/bin
ExecStart=$project_dir/scripts/export-opencode-conversations.sh
EOF

cat > "$unit_dir/$timer_name" <<EOF
[Unit]
Description=Run the OpenCode S3 export every five minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "$timer_name"
systemctl --user start "$service_name"
printf 'Automatic export enabled. Check it with: systemctl --user status %s\n' "$timer_name"
