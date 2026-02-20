#!/usr/bin/env bash
set -euo pipefail

echo "=== MAS-FRO Start ==="

# Ensure swap is active
if ! swapon --show | grep -q swapfile; then
    echo "[WARN] No swap detected. Run: sudo bash scripts/setup-swap.sh"
fi

# Start PostgreSQL
echo "Starting PostgreSQL..."
sudo systemctl start postgresql
sleep 2

if pg_isready -q; then
    echo "[OK] PostgreSQL is ready"
else
    echo "[FAIL] PostgreSQL failed to start"
    exit 1
fi

# Start backend
echo "Starting FastAPI backend..."
sudo systemctl start masfro-backend
sleep 3

if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "[OK] Backend is ready"
else
    echo "[WAIT] Backend starting up (may take 10-30s for graph loading)..."
    for i in $(seq 1 10); do
        sleep 3
        if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
            echo "[OK] Backend is ready"
            break
        fi
        echo "  ...waiting ($((i*3))s)"
    done
fi

# Start nginx (frontend)
echo "Starting nginx..."
sudo systemctl start nginx
sleep 1

if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "[OK] Frontend is ready"
else
    echo "[WARN] Frontend may not be accessible yet"
fi

echo ""
echo "=== MAS-FRO Running ==="
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""
free -h
