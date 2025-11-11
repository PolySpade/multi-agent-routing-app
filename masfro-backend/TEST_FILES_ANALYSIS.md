# Test Files Organization Analysis

**Date**: November 11, 2025
**Status**: Analysis Complete - Awaiting Approval

---

## Summary

Found **7 floating test files** (50 KB total) and **5 utility scripts** (19 KB) in masfro-backend root that need organization.

**Test Files**: Should be moved to organized `tests/` structure
**Utility Scripts**: Need decision on whether to keep, move to scripts/, or remove

---

## Floating Test Files (7 files - 50 KB)

### Integration Tests (6 files → `tests/integration/`)

#### 1. **test_integration.py** (11.1 KB)
- **Purpose**: Integration test script for MAS-FRO backend
- **Tests**: Module imports and component integration
- **Move to**: `tests/integration/test_integration.py`

#### 2. **test_agent_workflow.py** (8.9 KB)
- **Purpose**: Tests complete agent coordination workflow
- **Tests**: FloodAgent → HazardAgent → RoutingAgent workflow
- **Move to**: `tests/integration/test_agent_workflow.py`

#### 3. **test_services_only.py** (6.2 KB)
- **Purpose**: Quick test for real API services
- **Tests**: API services without full agent system (River Scraper, Weather, Dam, GeoTIFF)
- **Move to**: `tests/integration/test_services_only.py`

#### 4. **test_real_api_integration.py** (8.3 KB)
- **Purpose**: Real API integration tests
- **Tests**: External API integrations
- **Move to**: `tests/integration/test_real_api_integration.py`

#### 5. **test_hazard_integration.py** (8.7 KB)
- **Purpose**: HazardAgent integration test
- **Tests**: HazardAgent integration with other components
- **Move to**: `tests/integration/test_hazard_integration.py`

#### 6. **test_flood_agent_now.py** (6.3 KB)
- **Purpose**: Quick FloodAgent test with real API integration
- **Tests**: FloodAgent with PAGASA River Scraper, Weather Service, Dam Scraper
- **Move to**: `tests/integration/test_flood_agent_now.py`

### Unit Tests (1 file → `tests/unit/`)

#### 7. **test_datetime_encoder.py** (696 bytes)
- **Purpose**: DateTime encoder utility test
- **Tests**: Small utility function test
- **Move to**: `tests/unit/test_datetime_encoder.py`

---

## Utility/Debug Scripts (5 files - 19 KB)

These are **development/debugging scripts**, not tests. Need decision on what to do with them.

### Option 1: Keep in Root (if frequently used)
### Option 2: Move to `scripts/` folder (recommended)
### Option 3: Remove (if obsolete)

#### 1. **check_flood_tiff_coords.py** (5.2 KB)
- **Purpose**: Debug script to check GeoTIFF coordinates
- **Usage**: Development debugging tool
- **Recommendation**: Move to `scripts/` or remove if obsolete

#### 2. **check_tiff_simple.py** (4.8 KB)
- **Purpose**: Simple TIFF checking script
- **Usage**: Development debugging tool
- **Recommendation**: Move to `scripts/` or remove if obsolete

#### 3. **count_loc.py** (3.9 KB)
- **Purpose**: Lines of code counter for agent files
- **Usage**: Code metrics utility
- **Recommendation**: Move to `scripts/`

#### 4. **verify_graph_size.py** (1.6 KB)
- **Purpose**: Graph size verification script
- **Usage**: Development debugging tool
- **Recommendation**: Move to `scripts/` or remove if obsolete

#### 5. **run_data_collector.py** (3.8 KB)
- **Purpose**: Scheduled weather data collection script
- **Usage**: Runs OpenWeatherMap service on 15-second intervals
- **Recommendation**: Move to `scripts/` if still needed, or remove if obsolete

---

## Current tests/ Structure

```
tests/
├── __init__.py
├── fixtures/
│   └── __init__.py
├── integration/
│   └── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_hazard_agent.py
│   └── test_routing_agent.py
```

---

## Proposed Organization

### After Moving Test Files:

```
tests/
├── __init__.py
├── fixtures/
│   └── __init__.py
├── integration/
│   ├── __init__.py
│   ├── test_integration.py              # ✅ MOVED
│   ├── test_agent_workflow.py           # ✅ MOVED
│   ├── test_services_only.py            # ✅ MOVED
│   ├── test_real_api_integration.py     # ✅ MOVED
│   ├── test_hazard_integration.py       # ✅ MOVED
│   └── test_flood_agent_now.py          # ✅ MOVED
├── unit/
│   ├── __init__.py
│   ├── test_hazard_agent.py
│   ├── test_routing_agent.py
│   └── test_datetime_encoder.py         # ✅ MOVED
```

### Option A: Create scripts/ Folder (Recommended)

```
masfro-backend/
├── app/
├── tests/                               # ✅ Test files organized
├── scripts/                             # ✅ NEW: Utility scripts
│   ├── check_flood_tiff_coords.py
│   ├── check_tiff_simple.py
│   ├── count_loc.py
│   ├── verify_graph_size.py
│   └── run_data_collector.py
├── logs/
├── alembic/
├── pyproject.toml
└── uv.lock
```

### Option B: Remove Utility Scripts

If these scripts are obsolete or no longer needed, remove them entirely.

---

## Cleanup Commands

### 1. Move Test Files

```bash
cd masfro-backend

# Move integration tests
mv test_integration.py tests/integration/
mv test_agent_workflow.py tests/integration/
mv test_services_only.py tests/integration/
mv test_real_api_integration.py tests/integration/
mv test_hazard_integration.py tests/integration/
mv test_flood_agent_now.py tests/integration/

# Move unit test
mv test_datetime_encoder.py tests/unit/
```

### 2. Handle Utility Scripts (Choose One)

**Option A: Create scripts/ folder and move**
```bash
mkdir -p scripts
mv check_flood_tiff_coords.py scripts/
mv check_tiff_simple.py scripts/
mv count_loc.py scripts/
mv verify_graph_size.py scripts/
mv run_data_collector.py scripts/
```

**Option B: Remove if obsolete**
```bash
rm check_flood_tiff_coords.py check_tiff_simple.py count_loc.py verify_graph_size.py run_data_collector.py
```

---

## Verification Commands

```bash
# Verify test files moved
ls tests/integration/
ls tests/unit/

# Verify no floating test files remain
ls test*.py 2>/dev/null || echo "✅ No floating test files"

# Run tests to ensure they still work
uv run pytest tests/ -v
```

---

## Impact Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Floating test files | 7 | 0 | -100% |
| Organized integration tests | 0 | 6 | +6 |
| Organized unit tests | 2 | 3 | +50% |
| Root utility scripts | 5 | 0 or 5* | TBD |
| Clean structure | ❌ | ✅ | ✓ |

*Depends on whether you choose to move to scripts/ or remove

---

## Next Steps

1. **Review this analysis**
2. **Decide on utility scripts**: Keep in scripts/, remove, or keep in root?
3. **Approve test file organization**
4. **Execute cleanup commands**
5. **Run tests to verify**: `uv run pytest tests/ -v`
6. **Update .gitignore** if needed
7. **Commit organized structure**

---

## Questions for You

1. **Utility Scripts**: Do you want to:
   - A) Create `scripts/` folder and move them there (recommended)
   - B) Remove them (if obsolete)
   - C) Keep them in root (if frequently used)

2. **Are any of these utility scripts still needed for development?**
   - check_flood_tiff_coords.py
   - check_tiff_simple.py
   - count_loc.py
   - verify_graph_size.py
   - run_data_collector.py

---

**Recommendation**: Move test files to organized structure and create `scripts/` folder for utility scripts. This follows Python best practices and keeps the root directory clean.
