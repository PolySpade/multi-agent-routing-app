#!/usr/bin/env bash

echo "=== MAS-FRO Status ==="
echo ""

# Service status
echo "--- Services ---"
for svc in postgresql masfro-backend nginx; do
    status=$(systemctl is-active "$svc" 2>/dev/null) || status="inactive"
    case "$status" in
        active)   echo "  [OK]   $svc" ;;
        inactive) echo "  [OFF]  $svc" ;;
        failed)   echo "  [FAIL] $svc" ;;
        *)        echo "  [??]   $svc ($status)" ;;
    esac
done

echo ""

# Health checks
echo "--- Health Checks ---"
if pg_isready -q 2>/dev/null; then
    echo "  [OK]   PostgreSQL accepting connections"
else
    echo "  [FAIL] PostgreSQL not responding"
fi

if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  [OK]   FastAPI backend (http://localhost:8000)"
else
    echo "  [FAIL] FastAPI backend not responding"
fi

if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "  [OK]   Frontend (http://localhost:3000)"
else
    echo "  [FAIL] Frontend not responding"
fi

echo ""

# Memory
echo "--- Memory ---"
free -h
echo ""

# Swap
echo "--- Swap ---"
swapon --show 2>/dev/null || echo "  No swap configured"
