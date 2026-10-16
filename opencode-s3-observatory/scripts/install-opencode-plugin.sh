#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${HOME}/.config/opencode/plugins"
TARGET="${TARGET_DIR}/observatory-plugin.ts"
mkdir -p "${TARGET_DIR}"
ln -sfn "${ROOT}/opencode/observatory-plugin.ts" "${TARGET}"
printf 'OpenCode Observatory plugin installed:\n%s -> %s\n' "${TARGET}" "$(readlink -f "${TARGET}")"
printf 'Restart OpenCode to load it.\n'
