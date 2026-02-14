# Low-RAM Build Environment Design

**Date:** 2026-02-15
**Branch:** `low_ram_build_environment`
**Status:** Approved

## Problem

MAS-FRO needs to build and run the full stack (FastAPI backend + Next.js frontend + PostgreSQL) in a WSL2 environment with less than 1 GB of RAM. The current setup requires 800+ MB at runtime and 1.2+ GB during builds, exceeding the budget before counting the OS.

## Constraints

- **RAM:** <1 GB total in WSL2
- **Goal:** Build + run full stack in production mode
- **Database:** PostgreSQL on the same machine
- **Components:** Full stack (backend + frontend + DB)
- **LLM:** Ollama/Qwen runs externally (Windows host or remote), not locally

## Approach: Bare Metal (No Docker)

Docker's daemon overhead (~100-200 MB) is prohibitive at <1 GB. All services run directly on WSL2 with systemd management.

### Target RAM Budget

```
Component                      RAM
---------------------------------------
Linux kernel + OS overhead     ~80 MB
PostgreSQL (tuned)             ~50 MB
uvicorn + FastAPI (idle)       ~80 MB
  + on first route request     +200 MB (lazy loads osmnx/networkx/rasterio)
nginx (static frontend)        ~5 MB
Swap buffer                    ~2-4 GB on disk
---------------------------------------
Idle total:                    ~215 MB
After first request:           ~415 MB
Build peak (sequential):       ~400 MB (Node.js build, then freed)
```

---

## Section 1: WSL2 Memory Configuration

### `.wslconfig` (Windows side: `C:\Users\<user>\.wslconfig`)

```ini
[wsl2]
memory=896MB
swap=4GB
swapFile=C:\\wsl-swap.vhdx
processors=2
```

### Swap inside WSL2

Additional swap file for overflow:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
# Persist in /etc/fstab: /swapfile none swap sw 0 0
```

Set `vm.swappiness=60` via `/etc/sysctl.d/99-swappiness.conf`.

---

## Section 2: PostgreSQL Minimal-Memory Configuration

Override file: `config/postgresql-lowram.conf`

```ini
shared_buffers = 32MB
work_mem = 1MB
maintenance_work_mem = 16MB
effective_cache_size = 64MB
max_connections = 10
superuser_reserved_connections = 1
wal_buffers = 1MB
min_wal_size = 32MB
max_wal_size = 128MB
autovacuum_max_workers = 1
autovacuum_naptime = 5min
log_min_messages = warning
```

SQLAlchemy connection pool: `pool_size=3, max_overflow=2`.

**Estimated: ~50 MB** (vs ~200 MB default).

---

## Section 3: Frontend Static Export

Eliminate the Node.js runtime in production by pre-building Next.js to static files.

### `next.config.mjs` changes

```js
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  // ... existing webpack config stays
};
```

### API route migration

Three Next.js API routes must move to FastAPI:

- `src/app/api/places/autocomplete/route.js` -> `POST /api/places/autocomplete`
- `src/app/api/places/details/route.js` -> `GET /api/places/details`
- `src/app/api/places/geocode/route.js` -> `GET /api/places/geocode`

New file: `masfro-backend/app/api/places_endpoints.py`

### nginx serves static files

```nginx
server {
    listen 3000;
    root /path/to/masfro-frontend/out;
    index index.html;

    location / {
        try_files $uri $uri.html $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Savings: ~80-120 MB** (Node.js process eliminated).

---

## Section 4: Python Backend Memory Optimization

### Layer 1: Lazy imports

Move heavy top-level imports inside functions:

| Module | Files | Approx. Savings |
|--------|-------|-----------------|
| `osmnx` | `graph_manager.py` | ~100-150 MB |
| `rasterio` | `geotiff_service.py` | ~30-50 MB |
| `pandas` | `main.py`, `routing_agent.py`, 4 services | ~50-70 MB |
| `numpy` | `geotiff_service.py`, `dam_water_scraper_service.py` | ~30-40 MB |
| `selenium` | `river_scraper_service.py` | ~20-30 MB |
| `networkx` | `algorithms/*.py` | ~20-30 MB |

Already lazy (no change needed): spaCy, joblib, ollama.

### Layer 2: Single uvicorn worker

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --limit-max-requests 1000
```

### Layer 3: Sequential startup in FastAPI lifespan

```
1. PostgreSQL connection (light)
2. Graph environment (heavy - osmnx)
3. Agents initialized one-by-one
4. Scheduler starts last
```

### Layer 4: Feature flags via environment variables

```bash
MASFRO_LOW_RAM=true
MASFRO_DISABLE_SCHEDULER=false
MASFRO_DISABLE_SELENIUM=true
MASFRO_DISABLE_LLM=true
MASFRO_SCHEDULER_INTERVAL=15
```

**Estimated runtime: ~250-350 MB**.

---

## Section 5: Build Scripts + Service Orchestration

### New scripts

| Script | Purpose |
|--------|---------|
| `scripts/build.sh` | Sequential build: frontend (npm) then backend (uv sync) |
| `scripts/start.sh` | Start all services via systemctl |
| `scripts/stop.sh` | Graceful shutdown in reverse order |
| `scripts/status.sh` | Health check + memory report |
| `scripts/restart.sh` | stop + start |
| `scripts/setup-swap.sh` | Create and enable swap files |
| `scripts/setup-systemd.sh` | Install systemd unit files |

### Build order (never parallel)

```
Phase 1: npm install && next build   (peaks ~400 MB, then Node exits)
Phase 2: uv sync                     (peaks ~200 MB, then installer exits)
```

### systemd services

**`masfro-backend.service`:**
- `After=postgresql.service`, `Requires=postgresql.service`
- `ExecStart=.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --limit-max-requests 1000`
- `Environment=MASFRO_LOW_RAM=true`
- `Restart=on-failure`, `RestartSec=5`
- `MemoryMax=400M`

**`masfro-frontend.service`** (nginx):
- `After=masfro-backend.service`
- `ExecStart=/usr/sbin/nginx -c /etc/nginx/conf.d/masfro.conf`
- `MemoryMax=32M`

---

## Section 6: File Change Map

### New files

```
scripts/build.sh
scripts/start.sh
scripts/stop.sh
scripts/status.sh
scripts/restart.sh
scripts/setup-swap.sh
scripts/setup-systemd.sh
config/postgresql-lowram.conf
config/nginx-masfro.conf
config/masfro-backend.service
config/masfro-frontend.service
config/wslconfig-example
masfro-backend/app/api/places_endpoints.py
```

### Modified files

| File | Change |
|------|--------|
| `masfro-frontend/next.config.mjs` | Add `output: 'export'`, `images: { unoptimized: true }` |
| `masfro-backend/app/main.py` | Register places router, low-RAM env checks, sequential agent init |
| `masfro-backend/app/core/config.py` | Add `MASFRO_LOW_RAM`, `MASFRO_DISABLE_SELENIUM`, etc. |
| `masfro-backend/app/environment/graph_manager.py` | Lazy `import osmnx` |
| `masfro-backend/app/services/geotiff_service.py` | Lazy `import rasterio`, `import numpy` |
| `masfro-backend/app/services/river_scraper_service.py` | Lazy `import selenium`, skip if disabled |
| `masfro-backend/app/services/dam_water_scraper_service.py` | Lazy `import pandas`, `import numpy` |
| `masfro-backend/app/agents/routing_agent.py` | Lazy `import pandas` |
| `masfro-backend/app/database/repository.py` | Lazy `import pandas` |
| `masfro-backend/app/algorithms/path_optimizer.py` | Lazy `import networkx` |
| `masfro-backend/app/algorithms/risk_aware_astar.py` | Lazy `import networkx` |

### Removed files

```
masfro-frontend/src/app/api/places/autocomplete/route.js
masfro-frontend/src/app/api/places/details/route.js
masfro-frontend/src/app/api/places/geocode/route.js
```

### Untouched

- Agent logic (flood, hazard, scout, routing, evacuation, orchestrator)
- Communication layer (ACL protocol, message queue)
- Database models and migrations
- Frontend components (except API URL for places calls)
