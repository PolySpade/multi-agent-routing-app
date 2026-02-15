#!/usr/bin/env bash
set -euo pipefail

# Install MAS-FRO systemd services and configs
# Run with: sudo bash scripts/setup-systemd.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_DIR/config"

echo "=== MAS-FRO systemd Setup ==="
echo "Project: $PROJECT_DIR"

# Install PostgreSQL low-RAM config
PG_CONF_DIR=$(find /etc/postgresql -name "conf.d" -type d 2>/dev/null | head -1)
if [ -n "$PG_CONF_DIR" ]; then
    cp "$CONFIG_DIR/postgresql-lowram.conf" "$PG_CONF_DIR/lowram.conf"
    echo "[OK] PostgreSQL low-RAM config -> $PG_CONF_DIR/lowram.conf"
else
    echo "[SKIP] PostgreSQL conf.d not found — apply config manually"
fi

# Install nginx config
if [ -d /etc/nginx/sites-available ]; then
    cp "$CONFIG_DIR/nginx-masfro.conf" /etc/nginx/sites-available/masfro
    ln -sf /etc/nginx/sites-available/masfro /etc/nginx/sites-enabled/masfro
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    echo "[OK] nginx config installed"
else
    echo "[SKIP] nginx sites-available not found — install nginx first"
fi

# Install systemd services
cp "$CONFIG_DIR/masfro-backend.service" /etc/systemd/system/
cp "$CONFIG_DIR/masfro-frontend.service" /etc/systemd/system/
systemctl daemon-reload
echo "[OK] systemd services installed"

# Enable services
systemctl enable masfro-backend
systemctl enable masfro-frontend
echo "[OK] Services enabled"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Restart PostgreSQL: sudo systemctl restart postgresql"
echo "  2. Build the app:      bash scripts/build.sh"
echo "  3. Start services:     bash scripts/start.sh"
