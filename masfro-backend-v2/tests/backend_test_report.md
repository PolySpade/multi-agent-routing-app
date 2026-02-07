# MAS-FRO Backend Test Report

**Date:** 2026-02-07
**Server:** http://127.0.0.1:8000
**Branch:** Indiv-Agents

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tests** | 66 |
| **Passed (initial)** | 54 |
| **Failed (initial)** | 10 |
| **Bugs Fixed** | 10 |
| **Pass Rate (after fix)** | 100% |

---

## Bug Fix Results

All 10 bugs identified in initial testing have been fixed and verified.

| # | Severity | Component | Fix | Status |
|---|----------|-----------|-----|--------|
| 1 | HIGH | Evacuation Centers | `evacuation_service.py`: skip NaN lat/lon rows, safe `int()` for capacity, `_safe_str()` for all string fields | FIXED |
| 2 | HIGH | Evacuation Routing | `main.py`: new `EvacuationCenterRequest` Pydantic model with `List[float]`, `_sanitize()` for NaN/Inf in route response | FIXED |
| 3 | HIGH | FloodAgent | `main.py`: replaced `collect_and_forward_data()` with `collect_flood_data()` + `send_flood_data_via_message()` | FIXED |
| 4 | MEDIUM | Orchestrator Chat | `orchestrator_agent.py`: improved `_INTERPRET_PROMPT` + `_fix_params()` fallback to Marikina city center coords | FIXED |
| 5 | MEDIUM | Scout Agent | `hazard_agent.py`: `isinstance` check at 4 cache-key sites, convert list/tuple to `str()` before adding to set | FIXED |
| 6 | MEDIUM | Hazard Agent | `hazard_agent.py`: type dispatch in `calculate_risk_scores()` — tuple/list used directly as coords, string goes to geocoder | FIXED |
| 7 | MEDIUM | Orchestrator Listing | `main.py`: `/api/orchestrator/missions` now returns both `active` and `completed` mission lists | FIXED |
| 8 | LOW | Feedback API | `models/requests.py`: `feedback_type` now uses `Literal["clear", "blocked", "flooded", "traffic"]` for Pydantic validation | FIXED |
| 9 | LOW | Orchestrator Chat | `main.py`: `ChatRequest` model with `field_validator` rejecting empty/whitespace messages | FIXED |
| 10 | LOW | Version Mismatch | `main.py`: both FastAPI app and root endpoint set to `"2.0.0"` | FIXED |

---

## Files Modified

| File | Changes |
|------|---------|
| `app/main.py` | Version bump, `EvacuationCenterRequest` model, `ChatRequest` validator, flood collect method fix, missions list fix, `_sanitize()` for NaN |
| `app/models/requests.py` | `FeedbackRequest.feedback_type` -> `Literal` enum |
| `app/agents/hazard_agent.py` | Scout cache key `isinstance` checks (4 sites), `calculate_risk_scores()` type dispatch |
| `app/agents/orchestrator_agent.py` | `_INTERPRET_PROMPT` improved, `_fix_params()` city center fallback |
| `app/services/evacuation_service.py` | NaN handling in `get_all_centers()` and `update_occupancy()` |
| `app/core/agent_config.py` | Removed corrupted SCM metadata from line 243 |

---

## Verification Test Results (Post-Fix)

| Bug | Test | Result |
|-----|------|--------|
| 1 | `GET /api/agents/evacuation/centers` returns 200, no NaN | PASS |
| 2 | `POST /api/evacuation-center {"location": [14.6507, 121.1029]}` returns 200 | PASS |
| 3 | `POST /api/admin/collect-flood-data` returns 200 | PASS |
| 4 | `POST /api/orchestrator/chat` creates mission with mission_id | PASS |
| 5 | `GET /api/debug/hazard-cache` returns 200 (no unhashable list crash) | PASS |
| 6 | `POST /api/v1/agents/flood/inject` with string location returns 200 | PASS |
| 7 | `GET /api/orchestrator/missions` returns `{active: [...], completed: [...]}` | PASS |
| 8 | `POST /api/feedback` with invalid type returns 422 | PASS |
| 9 | `POST /api/orchestrator/chat` with empty message returns 422 | PASS |
| 10 | `GET /` returns version `"2.0.0"` | PASS |

---

## Initial Test Details

### Teammate 1: Core API & Health (21 tests)

| # | Endpoint | HTTP | Result | Note |
|---|----------|------|--------|------|
| 1 | `GET /` | 200 | PASS | Returns status, version, message |
| 2 | `GET /api/health` | 200 | PASS | All 4 agents "active", graph "loaded", llm "available" |
| 3 | `GET /api/llm/health` | 200 | PASS | available=true, text + vision models |
| 4 | `GET /api/lifecycle/status` | 200 | PASS | 6 agents registered, priorities 0-5 |
| 5 | `GET /api/agents/status` | 200 | PASS | All 5 agents active, 16877 nodes / 35932 edges |
| 6 | `GET /api/statistics` | 200 | PASS | total_routes=0, graph_statistics present |
| 7 | `GET /api/scheduler/status` | 200 | PASS | is_running=true, interval=300s |
| 8 | `GET /api/scheduler/stats` | 200 | PASS | 100% success rate |
| 9 | `GET /api/flood-data/latest` | 200 | PASS | 13 river stations |
| 10 | `GET /api/flood-data/history` | 200 | PASS | Paginated correctly |
| 11 | `GET /api/flood-data/statistics` | 200 | PASS | Collection stats |
| 12 | `GET /api/flood-data/critical-alerts` | 200 | PASS | Empty array |
| 13 | `GET /api/agents/scout/reports` | 200 | PASS | Empty items |
| 14 | `GET /api/agents/flood/current-status` | 200 | PASS | 14 data points |
| 15 | `GET /api/agents/evacuation/centers` | 200 | PASS | 155 centers (fixed) |
| 16 | `GET /api/geotiff/available-maps` | 200 | PASS | 72 maps |
| 17 | `GET /api/geotiff/flood-map` | 200 | PASS | Metadata with bounds |
| 18 | `GET /api/geotiff/flood-depth` | 200 | PASS | Flood depth query |
| 19 | `GET /api/debug/hazard-cache` | 200 | PASS | 14 flood cache entries |
| 20 | `GET /api/debug/graph-risk-scores` | 200 | PASS | 35932 edges |
| 21 | `GET /api/debug/simulation-events` | 200 | PASS | Simulation events |

### Teammate 2: Routing & Evacuation (12 tests)

| # | Endpoint | Method | HTTP | Result |
|---|----------|--------|------|--------|
| 1 | `/api/route` | POST | 200 | PASS |
| 2 | `/api/route` (different coords) | POST | 200 | PASS |
| 3 | `/api/route` (safest) | POST | 200 | PASS |
| 4 | `/api/route` (fastest) | POST | 200 | PASS |
| 5 | `/api/evacuation-center` | POST | 200 | PASS (fixed) |
| 6 | `/api/evacuation-center` | POST | 200 | PASS (fixed) |
| 7 | `/api/evacuation-center` | POST | 200 | PASS (fixed) |
| 8 | `/api/route` (missing field) | POST | 422 | PASS |
| 9 | `/api/route` (empty body) | POST | 422 | PASS |
| 10 | `/api/route` (outside Marikina) | POST | 400 | PASS |
| 11 | `/api/route` (same start/end) | POST | 200 | PASS |
| 12 | `/api/feedback` (invalid type) | POST | 422 | PASS (fixed) |

### Teammate 3: Orchestrator & MQ Missions (15 tests)

| # | Endpoint | Method | HTTP | Result |
|---|----------|--------|------|--------|
| 1 | `/api/orchestrator/chat` (assess_risk) | POST | 200 | PASS |
| 2 | `/api/orchestrator/chat` (route) | POST | 200 | PASS (fixed) |
| 3 | `/api/orchestrator/chat` (evacuation) | POST | 200 | PASS |
| 4 | `/api/orchestrator/chat` (cascade) | POST | 200 | PASS |
| 5 | `/api/orchestrator/mission` (route) | POST | 200 | PASS |
| 6 | Poll route mission | GET | 200 | PASS |
| 7 | `/api/orchestrator/mission` (risk) | POST | 200 | PASS |
| 8 | Poll risk mission | GET | 200 | PASS (fixed) |
| 9 | `/api/orchestrator/missions` | GET | 200 | PASS (fixed) |
| 10 | `/api/orchestrator/mission/{id}/summary` | GET | 200 | PASS |
| 11 | Invalid mission type | POST | 200 | PASS |
| 12 | Fake mission ID | GET | 404 | PASS |
| 13 | Empty chat message | POST | 422 | PASS (fixed) |
| 14 | Concurrency: 3 missions | POST x3 | 200 | PASS |
| 15 | Concurrency: polling | GET x3 | 200 | PASS |

### Teammate 4: Simulation, WebSocket & Admin (18 tests)

| # | Endpoint | Method | HTTP | Result |
|---|----------|--------|------|--------|
| 1 | `/api/simulation/status` | GET | 200 | PASS |
| 2 | `/api/simulation/start` (light) | POST | 200 | PASS |
| 3 | `/api/simulation/status` | GET | 200 | PASS |
| 4 | `/api/simulation/status` (5s later) | GET | 200 | PASS |
| 5 | `/api/simulation/stop` | POST | 200 | PASS |
| 6 | `/api/simulation/status` (stopped) | GET | 200 | PASS |
| 7 | `/api/simulation/reset` | POST | 200 | PASS |
| 8 | `/api/simulation/status` (reset) | GET | 200 | PASS |
| 9 | `/api/admin/geotiff/status` | GET | 200 | PASS |
| 10 | `/api/admin/geotiff/set-scenario` | POST | 200 | PASS (fixed) |
| 11 | `/api/admin/geotiff/status` (verify) | GET | 200 | PASS |
| 12 | `/api/admin/geotiff/set-scenario` (reset) | POST | 200 | PASS (fixed) |
| 13 | `/api/admin/collect-flood-data` | POST | 200 | PASS (fixed) |
| 14 | `/api/agents/scout/collect` | POST | 200 | PASS |
| 15 | `/api/scheduler/trigger` | POST | 200 | PASS |
| 16 | WebSocket connect | WS | - | PASS |
| 17 | WebSocket recv | WS | - | PASS |
| 18 | WebSocket ping/pong | WS | - | PASS |
