#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== MAS-FRO Restart ==="
bash "$SCRIPT_DIR/stop.sh"
sleep 2
bash "$SCRIPT_DIR/start.sh"
