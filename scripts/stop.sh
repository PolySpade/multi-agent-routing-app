#!/usr/bin/env bash
set -euo pipefail

echo "=== MAS-FRO Stop ==="

echo "Stopping nginx..."
sudo systemctl stop nginx 2>/dev/null || true

echo "Stopping FastAPI backend..."
sudo systemctl stop masfro-backend 2>/dev/null || true

echo "Stopping PostgreSQL..."
sudo systemctl stop postgresql 2>/dev/null || true

echo ""
echo "=== All services stopped ==="
