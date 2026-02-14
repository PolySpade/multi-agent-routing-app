# Low-RAM Build Environment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run the full MAS-FRO stack (FastAPI + static Next.js + PostgreSQL) on WSL2 with <1 GB RAM.

**Architecture:** Bare metal (no Docker). Next.js pre-built as static files served by nginx. FastAPI runs single-worker uvicorn with lazy-loaded heavy modules. PostgreSQL tuned to ~50 MB. All services managed by systemd with memory limits. Swap provides overflow for build peaks.

**Tech Stack:** Python/FastAPI, Next.js (static export), nginx, PostgreSQL, systemd, WSL2

**Design doc:** `docs/plans/2026-02-15-low-ram-build-environment-design.md`

---

## Task 1: Add Low-RAM Configuration Settings

**Files:**
- Modify: `masfro-backend/app/core/config.py`

**Step 1: Add low-RAM environment variables to Settings class**

Add these fields after the `LOAD_INITIAL_FLOOD_DATA` line (line 54) in the `Settings` class:

```python
    # ========== LOW-RAM MODE ==========
    MASFRO_LOW_RAM: bool = False
    MASFRO_DISABLE_SELENIUM: bool = False
    MASFRO_DISABLE_LLM: bool = False
    MASFRO_DISABLE_SCHEDULER: bool = False
    MASFRO_SCHEDULER_INTERVAL: int = 5  # minutes
```

**Step 2: Add helper method**

Add after the `is_llm_enabled` method:

```python
    def is_low_ram(self) -> bool:
        """Check if running in low-RAM mode."""
        return self.MASFRO_LOW_RAM

    def is_selenium_enabled(self) -> bool:
        """Check if Selenium scraping is enabled."""
        return not self.MASFRO_DISABLE_SELENIUM

    def is_scheduler_enabled(self) -> bool:
        """Check if the flood data scheduler is enabled."""
        return not self.MASFRO_DISABLE_SCHEDULER
```

**Step 3: Commit**

```bash
git add masfro-backend/app/core/config.py
git commit -m "feat: add low-RAM mode configuration settings"
```

---

## Task 2: Lazy Imports in graph_manager.py

**Files:**
- Modify: `masfro-backend/app/environment/graph_manager.py`

**Step 1: Remove top-level osmnx import**

Replace lines 2-3:

```python
import osmnx as ox
import networkx as nx
```

With:

```python
# networkx and osmnx imported lazily to reduce startup memory
```

**Step 2: Add lazy import inside `_load_graph_from_file`**

At the top of the `_load_graph_from_file` method body, add:

```python
        import osmnx as ox
```

**Step 3: Add lazy networkx import where needed**

In `get_graph` return type and anywhere `nx` is referenced, add local imports. The only direct `nx` usage is the return type hint. Since `nx.MultiDiGraph` is only a type hint, we can use a string annotation or import conditionally.

Replace the `get_graph` method:

```python
    def get_graph(self):
        """
        Get the graph instance.

        Returns:
            NetworkX MultiDiGraph instance
        """
        return self.graph
```

**Step 4: Verify the module still works**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
python -c "from app.environment.graph_manager import DynamicGraphEnvironment; print('OK')"
```

Expected: `OK` printed (no osmnx loaded yet since graph file hasn't been loaded).

**Step 5: Commit**

```bash
git add masfro-backend/app/environment/graph_manager.py
git commit -m "feat: lazy import osmnx in graph_manager to reduce startup memory"
```

---

## Task 3: Lazy Imports in geotiff_service.py

**Files:**
- Modify: `masfro-backend/app/services/geotiff_service.py`

**Step 1: Remove top-level numpy and rasterio imports**

Replace lines 25-34:

```python
import numpy as np

# Configure GDAL environment variables BEFORE importing rasterio
# These settings handle non-standard GeoTIFF coordinate reference systems
os.environ['GTIFF_SRS_SOURCE'] = 'EPSG'  # Use official EPSG parameters over GeoTIFF keys
os.environ['GTIFF_HONOUR_NEGATIVE_SCALEY'] = 'YES'  # Handle negative ScaleY values correctly
os.environ['CPL_LOG'] = '/dev/null'  # Suppress GDAL C-level log messages

import rasterio
from rasterio.transform import rowcol
```

With:

```python
# numpy and rasterio imported lazily to reduce startup memory
# GDAL env vars are set before first rasterio import in _ensure_rasterio()
```

**Step 2: Add `_ensure_rasterio` helper method to GeoTIFFService class**

Add as the first method after `__init__`:

```python
    def _ensure_rasterio(self):
        """Lazy-load rasterio and numpy, setting GDAL env vars first."""
        import numpy as np
        os.environ.setdefault('GTIFF_SRS_SOURCE', 'EPSG')
        os.environ.setdefault('GTIFF_HONOUR_NEGATIVE_SCALEY', 'YES')
        os.environ.setdefault('CPL_LOG', '/dev/null')
        import rasterio
        return np, rasterio
```

**Step 3: Update all methods that use numpy/rasterio**

In `load_flood_map`, replace direct usage:

```python
    @lru_cache(maxsize=32)
    def load_flood_map(self, return_period="rr01", time_step=1):
        # ... validation stays the same ...

        np, rasterio = self._ensure_rasterio()

        # rest of method uses np and rasterio as before
```

In `get_flood_depth_at_point`:

```python
        np, _ = self._ensure_rasterio()
```

In `__init__`, remove type hints that reference `np.ndarray`:

```python
        self._cache: Dict[str, Any] = {}
```

**Step 4: Update the global `_geotiff_service` type hint**

Replace:

```python
_geotiff_service: Optional[GeoTIFFService] = None
```

With:

```python
_geotiff_service = None
```

**Step 5: Verify import works without loading rasterio**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
python -c "from app.services.geotiff_service import GeoTIFFService; print('OK')"
```

Expected: `OK` (rasterio not loaded yet).

**Step 6: Commit**

```bash
git add masfro-backend/app/services/geotiff_service.py
git commit -m "feat: lazy import rasterio/numpy in geotiff_service"
```

---

## Task 4: Lazy Imports in river_scraper_service.py

**Files:**
- Modify: `masfro-backend/app/services/river_scraper_service.py`

**Step 1: Remove top-level selenium and pandas imports**

Replace lines 13-24:

```python
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
```

With:

```python
from io import StringIO
from bs4 import BeautifulSoup

# selenium and pandas imported lazily to reduce startup memory
```

**Step 2: Add lazy import at the start of each method that uses selenium/pandas**

In methods that use `pd`:

```python
        import pandas as pd
```

In methods that use selenium (the `scrape_*` methods or wherever `webdriver` is used):

```python
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, WebDriverException
```

**Step 3: Add feature flag check**

At the top of the main scraping method(s), add an early return if selenium is disabled:

```python
        from app.core.config import settings
        if not settings.is_selenium_enabled():
            logger.info("Selenium disabled (MASFRO_DISABLE_SELENIUM=true), skipping scrape")
            return None
```

**Step 4: Verify**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
python -c "from app.services.river_scraper_service import RiverScraperService; print('OK')"
```

Expected: `OK` (selenium not loaded).

**Step 5: Commit**

```bash
git add masfro-backend/app/services/river_scraper_service.py
git commit -m "feat: lazy import selenium/pandas in river_scraper_service"
```

---

## Task 5: Lazy Imports in dam_water_scraper_service.py

**Files:**
- Modify: `masfro-backend/app/services/dam_water_scraper_service.py`

**Step 1: Remove top-level pandas and numpy imports**

Replace lines 15-16:

```python
import pandas as pd
```
and line 18:
```python
import numpy as np
```

With:

```python
# pandas and numpy imported lazily to reduce startup memory
```

**Step 2: Add lazy imports inside methods that use pd/np**

At the start of each method body that references `pd` or `np`:

```python
        import pandas as pd
        import numpy as np
```

**Step 3: Verify**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
python -c "from app.services.dam_water_scraper_service import *; print('OK')"
```

**Step 4: Commit**

```bash
git add masfro-backend/app/services/dam_water_scraper_service.py
git commit -m "feat: lazy import pandas/numpy in dam_water_scraper_service"
```

---

## Task 6: Lazy Imports in routing_agent.py and repository.py

**Files:**
- Modify: `masfro-backend/app/agents/routing_agent.py`
- Modify: `masfro-backend/app/database/repository.py`

**Step 1: In routing_agent.py, move `import pandas as pd` (line 87) inside methods**

Remove the top-level import. Add `import pandas as pd` at the start of each method that uses `pd`.

**Step 2: In repository.py, move `import pandas as pd` (line 14) inside methods**

Remove the top-level import. Add `import pandas as pd` at the start of each method that uses `pd`.

**Step 3: Verify both imports**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
python -c "from app.agents.routing_agent import RoutingAgent; print('OK')"
python -c "from app.database.repository import FloodDataRepository; print('OK')"
```

**Step 4: Commit**

```bash
git add masfro-backend/app/agents/routing_agent.py masfro-backend/app/database/repository.py
git commit -m "feat: lazy import pandas in routing_agent and repository"
```

---

## Task 7: Lazy Import pandas in main.py

**Files:**
- Modify: `masfro-backend/app/main.py`

**Step 1: Remove top-level pandas import**

Remove line 33:

```python
import pandas as pd
```

**Step 2: Add `import pandas as pd` inside any function in main.py that uses `pd`**

Search for `pd.` usage in main.py and add the import at the start of each function body.

**Step 3: Verify the app still starts**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
python -c "from app.main import app; print('OK')"
```

**Step 4: Commit**

```bash
git add masfro-backend/app/main.py
git commit -m "feat: lazy import pandas in main.py"
```

---

## Task 8: Migrate Places API Routes to FastAPI Backend

**Files:**
- Create: `masfro-backend/app/api/places_endpoints.py`
- Modify: `masfro-backend/app/api/__init__.py`
- Modify: `masfro-backend/app/main.py` (register router)

**Step 1: Create `places_endpoints.py`**

```python
"""
Google Places API proxy endpoints.

Migrated from Next.js API routes to FastAPI for static frontend export.
These endpoints proxy requests to the Google Maps API, keeping the
API key server-side.
"""

import logging
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/places", tags=["places"])

GOOGLE_API_KEY = settings.GOOGLE_API_KEY


class AutocompleteRequest(BaseModel):
    input: str
    sessionToken: str
    components: str = "country:ph"


class DetailsRequest(BaseModel):
    placeId: str
    sessionToken: str
    fields: str = "formatted_address,geometry/location,name"


class GeocodeRequest(BaseModel):
    address: str
    components: str = "country:PH"


@router.post("/autocomplete")
async def places_autocomplete(req: AutocompleteRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key is not configured.")

    if not req.input or len(req.input.strip()) < 3:
        return {"status": "ZERO_RESULTS", "predictions": []}

    params = {
        "input": req.input,
        "key": GOOGLE_API_KEY,
        "sessiontoken": req.sessionToken,
        "components": req.components,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/place/autocomplete/json",
            params=params,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Autocomplete request failed.")

    return resp.json()


@router.post("/details")
async def places_details(req: DetailsRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key is not configured.")

    params = {
        "place_id": req.placeId,
        "key": GOOGLE_API_KEY,
        "sessiontoken": req.sessionToken,
        "fields": req.fields,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params=params,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Place details request failed.")

    return resp.json()


@router.post("/geocode")
async def places_geocode(req: GeocodeRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key is not configured.")

    if not req.address or len(req.address.strip()) < 3:
        return {"status": "ZERO_RESULTS", "results": []}

    params = {
        "address": req.address.strip(),
        "key": GOOGLE_API_KEY,
        "components": req.components,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params=params,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Geocoding request failed.")

    return resp.json()
```

**Step 2: Add httpx dependency**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
uv add httpx
```

**Step 3: Register router in `__init__.py`**

Add to imports in `masfro-backend/app/api/__init__.py`:

```python
from .places_endpoints import router as places_router
```

Add `"places_router"` to `__all__`.

**Step 4: Register router in `main.py`**

Find where `app.include_router(graph_router)` is (line 404) and add:

```python
from app.api.places_endpoints import router as places_router
app.include_router(places_router)
```

**Step 5: Commit**

```bash
git add masfro-backend/app/api/places_endpoints.py masfro-backend/app/api/__init__.py masfro-backend/app/main.py masfro-backend/pyproject.toml masfro-backend/uv.lock
git commit -m "feat: migrate places API routes from Next.js to FastAPI"
```

---

## Task 9: Update Frontend to Call Backend Places API

**Files:**
- Modify: `masfro-frontend/src/components/LocationSearch.js`

**Step 1: Update the geocode fetch URL**

In `LocationSearch.js` line 38, change:

```javascript
const response = await fetch('/api/places/geocode', {
```

To use the backend URL:

```javascript
const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
```

Add this constant at the top of the file (after imports), then update line 38:

```javascript
const response = await fetch(`${API_BASE}/api/places/geocode`, {
```

**Step 2: Commit**

```bash
git add masfro-frontend/src/components/LocationSearch.js
git commit -m "feat: point places API calls to FastAPI backend"
```

---

## Task 10: Configure Next.js Static Export

**Files:**
- Modify: `masfro-frontend/next.config.mjs`
- Remove: `masfro-frontend/src/app/api/places/autocomplete/route.js`
- Remove: `masfro-frontend/src/app/api/places/details/route.js`
- Remove: `masfro-frontend/src/app/api/places/geocode/route.js`

**Step 1: Update next.config.mjs**

Replace the entire file with:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  webpack: (config, { dev, isServer }) => {
    // Add support for .tif and .tiff files
    config.module.rules.push({
      test: /\.(tif|tiff)$/,
      type: 'asset/resource',
    });

    // Suppress source map warnings
    if (dev) {
      config.devtool = false;
    }

    return config;
  },
  productionBrowserSourceMaps: false,
  reactStrictMode: true,
};

export default nextConfig;
```

**Step 2: Remove old API routes**

```bash
rm masfro-frontend/src/app/api/places/autocomplete/route.js
rm masfro-frontend/src/app/api/places/details/route.js
rm masfro-frontend/src/app/api/places/geocode/route.js
rmdir masfro-frontend/src/app/api/places/autocomplete
rmdir masfro-frontend/src/app/api/places/details
rmdir masfro-frontend/src/app/api/places/geocode
rmdir masfro-frontend/src/app/api/places
rmdir masfro-frontend/src/app/api 2>/dev/null || true
```

**Step 3: Test static build**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-frontend
npm run build
```

Expected: Build succeeds and creates `out/` directory with static files.

Note: If the build fails due to dynamic features incompatible with static export, the error will indicate which page/component needs adjustment. Fix as needed.

**Step 4: Commit**

```bash
git add -A masfro-frontend/
git commit -m "feat: configure Next.js static export, remove API routes"
```

---

## Task 11: Create PostgreSQL Low-RAM Config

**Files:**
- Create: `config/postgresql-lowram.conf`

**Step 1: Create the config file**

```ini
# PostgreSQL configuration tuned for <1 GB RAM environments
# Copy to /etc/postgresql/*/main/conf.d/lowram.conf
# or include from postgresql.conf

# === Memory ===
shared_buffers = 32MB
work_mem = 1MB
maintenance_work_mem = 16MB
effective_cache_size = 64MB

# === Connections ===
max_connections = 10
superuser_reserved_connections = 1

# === WAL ===
wal_buffers = 1MB
min_wal_size = 32MB
max_wal_size = 128MB

# === Background Workers ===
autovacuum_max_workers = 1
autovacuum_naptime = 5min

# === Logging ===
log_min_messages = warning
```

**Step 2: Commit**

```bash
git add config/postgresql-lowram.conf
git commit -m "feat: add PostgreSQL low-RAM configuration"
```

---

## Task 12: Create nginx Configuration

**Files:**
- Create: `config/nginx-masfro.conf`

**Step 1: Create the nginx config**

```nginx
# MAS-FRO nginx configuration
# Serves static Next.js frontend and proxies API/WebSocket to FastAPI
#
# Install: sudo cp config/nginx-masfro.conf /etc/nginx/sites-available/masfro
#          sudo ln -s /etc/nginx/sites-available/masfro /etc/nginx/sites-enabled/
#          sudo nginx -t && sudo systemctl reload nginx

server {
    listen 3000;
    server_name localhost;

    # Static frontend files (Next.js export output)
    root /home/ajet/projects/multi-agent-routing-app/masfro-frontend/out;
    index index.html;

    # Frontend routes — serve static files or fallback to index.html
    location / {
        try_files $uri $uri.html $uri/ /index.html;
    }

    # Proxy API requests to FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    # Proxy WebSocket connections
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # Serve GeoTIFF data files
    location /data/ {
        proxy_pass http://127.0.0.1:8000;
    }

    # Minimize logging to save disk I/O
    access_log /var/log/nginx/masfro-access.log combined buffer=16k flush=5m;
    error_log /var/log/nginx/masfro-error.log warn;
}
```

**Step 2: Commit**

```bash
git add config/nginx-masfro.conf
git commit -m "feat: add nginx config for static frontend + API proxy"
```

---

## Task 13: Create systemd Service Files

**Files:**
- Create: `config/masfro-backend.service`
- Create: `config/masfro-frontend.service`

**Step 1: Create backend service**

```ini
# MAS-FRO FastAPI Backend Service
# Install: sudo cp config/masfro-backend.service /etc/systemd/system/
#          sudo systemctl daemon-reload
#          sudo systemctl enable masfro-backend

[Unit]
Description=MAS-FRO FastAPI Backend
After=postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=ajet
Group=ajet
WorkingDirectory=/home/ajet/projects/multi-agent-routing-app/masfro-backend
EnvironmentFile=/home/ajet/projects/multi-agent-routing-app/masfro-backend/.env
Environment=MASFRO_LOW_RAM=true
Environment=MASFRO_DISABLE_SELENIUM=true
Environment=MASFRO_DISABLE_LLM=true
ExecStart=/home/ajet/projects/multi-agent-routing-app/masfro-backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --limit-max-requests 1000
Restart=on-failure
RestartSec=5
MemoryMax=400M
StandardOutput=journal
StandardError=journal
SyslogIdentifier=masfro-backend

[Install]
WantedBy=multi-user.target
```

**Step 2: Create frontend service**

```ini
# MAS-FRO Frontend (nginx) Service
# Note: This is an override/dependency wrapper.
# nginx itself is managed by the system nginx service.
# This unit ensures nginx starts after the backend.
#
# If using a dedicated nginx config (not system-wide):
# Install: sudo cp config/masfro-frontend.service /etc/systemd/system/
#          sudo systemctl daemon-reload
#          sudo systemctl enable masfro-frontend

[Unit]
Description=MAS-FRO Frontend (nginx)
After=masfro-backend.service
Wants=masfro-backend.service

[Service]
Type=forking
PIDFile=/run/nginx-masfro.pid
ExecStartPre=/usr/sbin/nginx -t -c /etc/nginx/sites-available/masfro
ExecStart=/usr/sbin/nginx -c /etc/nginx/nginx.conf
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Restart=on-failure
MemoryMax=32M

[Install]
WantedBy=multi-user.target
```

**Step 3: Commit**

```bash
git add config/masfro-backend.service config/masfro-frontend.service
git commit -m "feat: add systemd service files for backend and frontend"
```

---

## Task 14: Create .wslconfig Example

**Files:**
- Create: `config/wslconfig-example`

**Step 1: Create the file**

```ini
# WSL2 configuration for low-RAM environments
# Copy this file to C:\Users\<your-username>\.wslconfig
# Then restart WSL: wsl --shutdown

[wsl2]
memory=896MB
swap=4GB
swapFile=C:\\wsl-swap.vhdx
processors=2
```

**Step 2: Commit**

```bash
git add config/wslconfig-example
git commit -m "feat: add .wslconfig example for WSL2 memory limits"
```

---

## Task 15: Create Swap Setup Script

**Files:**
- Create: `scripts/setup-swap.sh`

**Step 1: Create the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Setup swap for low-RAM WSL2 environments
# Run with: sudo bash scripts/setup-swap.sh

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
```

**Step 2: Make executable and commit**

```bash
chmod +x scripts/setup-swap.sh
git add scripts/setup-swap.sh
git commit -m "feat: add swap setup script for low-RAM environments"
```

---

## Task 16: Create systemd Setup Script

**Files:**
- Create: `scripts/setup-systemd.sh`

**Step 1: Create the script**

```bash
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
    # Remove default site to free port 80
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
```

**Step 2: Make executable and commit**

```bash
chmod +x scripts/setup-systemd.sh
git add scripts/setup-systemd.sh
git commit -m "feat: add systemd setup script"
```

---

## Task 17: Create Build Script

**Files:**
- Create: `scripts/build.sh`

**Step 1: Create the script**

```bash
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
```

**Step 2: Make executable and commit**

```bash
chmod +x scripts/build.sh
git add scripts/build.sh
git commit -m "feat: add sequential build script for low-RAM environments"
```

---

## Task 18: Create Start/Stop/Status/Restart Scripts

**Files:**
- Create: `scripts/start.sh`
- Create: `scripts/stop.sh`
- Create: `scripts/status.sh`
- Create: `scripts/restart.sh`

**Step 1: Create start.sh**

```bash
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
```

**Step 2: Create stop.sh**

```bash
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
```

**Step 3: Create status.sh**

```bash
#!/usr/bin/env bash

echo "=== MAS-FRO Status ==="
echo ""

# Service status
echo "--- Services ---"
for svc in postgresql masfro-backend nginx; do
    status=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
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
```

**Step 4: Create restart.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== MAS-FRO Restart ==="
bash "$SCRIPT_DIR/stop.sh"
sleep 2
bash "$SCRIPT_DIR/start.sh"
```

**Step 5: Make all executable and commit**

```bash
chmod +x scripts/start.sh scripts/stop.sh scripts/status.sh scripts/restart.sh
git add scripts/start.sh scripts/stop.sh scripts/status.sh scripts/restart.sh
git commit -m "feat: add start/stop/status/restart scripts"
```

---

## Task 19: Final Verification

**Step 1: Run a quick import check for all lazy-loaded modules**

```bash
cd /home/ajet/projects/multi-agent-routing-app/masfro-backend
python -c "
import sys
from app.main import app
# Check that heavy modules are NOT loaded at import time
heavy = ['osmnx', 'rasterio', 'selenium', 'spacy']
loaded = [m for m in heavy if m in sys.modules]
print(f'Heavy modules loaded at startup: {loaded or \"none (good!)\"} ')
print(f'Total modules: {len(sys.modules)}')
"
```

Expected: `Heavy modules loaded at startup: none (good!)`

Note: `pandas` and `networkx` may still appear because they're transitive deps of other imports. The big wins (osmnx, rasterio, selenium) should not be loaded.

**Step 2: Run status check**

```bash
bash scripts/status.sh
```

**Step 3: Commit any remaining changes**

```bash
git add -A
git status
# If there are changes:
git commit -m "chore: final cleanup for low-RAM build environment"
```
