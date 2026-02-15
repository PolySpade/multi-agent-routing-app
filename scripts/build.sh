#!/usr/bin/env bash
set -euo pipefail

# Sequential build for low-RAM environments
# Builds frontend first (high peak RAM), then backend deps
# NEVER runs both in parallel

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_DIR/masfro-frontend"
BACKEND_DIR="$PROJECT_DIR/masfro-backend"

echo "=== MAS-FRO Build (Low-RAM Mode) ==="
echo "Project: $PROJECT_DIR"
echo ""

# Phase 1: Frontend (Node.js build peaks at ~400 MB)
echo "--- Phase 1: Frontend Build ---"
echo "Installing npm dependencies..."
cd "$FRONTEND_DIR"
NODE_OPTIONS="--max-old-space-size=384" npm install --prefer-offline
echo ""

echo "Building static export..."
NODE_OPTIONS="--max-old-space-size=384" npm run build
echo ""

if [ -d "$FRONTEND_DIR/out" ]; then
    echo "[OK] Frontend built -> $FRONTEND_DIR/out/"
    echo "     $(find "$FRONTEND_DIR/out" -type f | wc -l) files"
else
    echo "[FAIL] Frontend build did not produce out/ directory"
    exit 1
fi

# Force Node.js garbage collection by letting process exit
echo "Waiting for Node.js memory to be reclaimed..."
sleep 2
echo ""

# Phase 2: Backend (Python deps)
echo "--- Phase 2: Backend Dependencies ---"
cd "$BACKEND_DIR"

if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Syncing Python dependencies..."
uv sync
echo ""
echo "[OK] Backend dependencies installed"

# Phase 3: Database migrations
echo ""
echo "--- Phase 3: Database Migrations ---"
cd "$BACKEND_DIR"
if [ -f ".env" ]; then
    source .venv/bin/activate
    alembic upgrade head 2>/dev/null && echo "[OK] Migrations applied" || echo "[SKIP] Migrations skipped (DB may not be running)"
    deactivate
else
    echo "[SKIP] No .env file — skipping migrations"
fi

echo ""
echo "=== Build Complete ==="
free -h
