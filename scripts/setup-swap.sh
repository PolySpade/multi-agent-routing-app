#!/usr/bin/env bash
set -euo pipefail

# Setup swap for low-RAM WSL2 environments
# Run with: sudo bash scripts/setup-swap.sh [size]

SWAP_SIZE="${1:-2G}"
SWAP_FILE="/swapfile"

echo "=== MAS-FRO Swap Setup ==="
echo "Swap size: $SWAP_SIZE"

if swapon --show | grep -q "$SWAP_FILE"; then
    echo "Swap already active at $SWAP_FILE"
    swapon --show
    exit 0
fi

if [ -f "$SWAP_FILE" ]; then
    echo "Swap file exists, activating..."
else
    echo "Creating swap file..."
    fallocate -l "$SWAP_SIZE" "$SWAP_FILE"
    chmod 600 "$SWAP_FILE"
    mkswap "$SWAP_FILE"
fi

swapon "$SWAP_FILE"

# Add to fstab if not already there
if ! grep -q "$SWAP_FILE" /etc/fstab; then
    echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
    echo "Added to /etc/fstab"
fi

# Set swappiness
if [ ! -f /etc/sysctl.d/99-swappiness.conf ]; then
    echo "vm.swappiness=60" > /etc/sysctl.d/99-swappiness.conf
    sysctl -p /etc/sysctl.d/99-swappiness.conf
    echo "Set vm.swappiness=60"
fi

echo ""
echo "=== Swap configured ==="
free -h
