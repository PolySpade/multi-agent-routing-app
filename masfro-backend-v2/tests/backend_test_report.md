# MAS-FRO Backend Test Report

**Date:** 2026-02-07
**Server:** http://127.0.0.1:8000
**Branch:** Indiv-Agents

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tests** | 66 |
| **Passed** | 54 |
| **Failed** | 10 |
| **Warnings** | 2 |
| **Skipped** | 0 |
| **Pass Rate** | 81.8% |

---

## Bugs Found

| # | Severity | Component | Description |
|---|----------|-----------|-------------|
| 1 | HIGH | Evacuation Centers | `GET /api/agents/evacuation/centers` returns 500: `cannot convert float NaN to integer` — NaN in CSV lat/lon data |
| 2 | HIGH | Evacuation Routing | `POST /api/evacuation-center` returns 500 even with valid array input — crash in `find_nearest_evacuation_center()` |
| 3 | HIGH | FloodAgent | `collect_and_forward_data()` method missing — breaks `/api/admin/collect-flood-data` and `/api/admin/geotiff/set-scenario` |
| 4 | MEDIUM | Orchestrator Chat | LLM fails to extract both `start` and `end` coords from NL route request; `_fix_params()` doesn't recover |
| 5 | MEDIUM | Scout Agent | `unhashable type: 'list'` when orchestrator passes location as list instead of tuple |
| 6 | MEDIUM | Hazard Agent | `'tuple' object has no attribute 'lower'` — location passed as tuple where string expected |
| 7 | MEDIUM | Orchestrator Listing | `GET /api/orchestrator/missions` returns `[]` — completed missions not included from `_completed_missions` deque |
| 8 | LOW | Feedback API | `POST /api/feedback` returns 500 for invalid feedback_type instead of 422 — no Pydantic-level validation |
| 9 | LOW | Orchestrator Chat | Empty message `""` not validated — LLM hallucinates a mission |
| 10 | LOW | Version Mismatch | Root `/` reports version "1.0.0", `/api/health` reports "2.0.0" |

---

## Teammate 1: Core API & Health (21 tests — 20 PASS, 1 FAIL)

| # | Endpoint | HTTP | Result | Note |
|---|----------|------|--------|------|
| 1 | `GET /` | 200 | PASS | Returns status, version ("1.0.0"), message |
| 2 | `GET /api/health` | 200 | PASS | All 4 agents "active", graph "loaded", llm "available", version "2.0.0" |
| 3 | `GET /api/llm/health` | 200 | PASS | available=true, text_model="llama3.2:latest", vision_model="moondream:latest" |
| 4 | `GET /api/lifecycle/status` | 200 | PASS | 6 agents registered, priorities 0-5 |
| 5 | `GET /api/agents/status` | 200 | PASS | All 5 agents active, 16877 nodes / 35932 edges, 155 evac centers |
| 6 | `GET /api/statistics` | 200 | PASS | total_routes=0, graph_statistics present |
| 7 | `GET /api/scheduler/status` | 200 | PASS | is_running=true, interval=300s |
| 8 | `GET /api/scheduler/stats` | 200 | PASS | 1 run, 100% success, 14 data points |
| 9 | `GET /api/flood-data/latest` | 200 | PASS | 13 river stations, all NORMAL risk |
| 10 | `GET /api/flood-data/history?page=1&page_size=5` | 200 | PASS | Paginated: 13 total, 3 pages |
| 11 | `GET /api/flood-data/statistics` | 200 | PASS | 62/62 collections, 100% success |
| 12 | `GET /api/flood-data/critical-alerts` | 200 | PASS | Empty array, correct shape |
| 13 | `GET /api/agents/scout/reports?page=1&page_size=5` | 200 | PASS | Empty items, pagination correct |
| 14 | `GET /api/agents/flood/current-status` | 200 | PASS | 14 data points, all with timestamps |
| 15 | `GET /api/agents/evacuation/centers` | 500 | **FAIL** | `cannot convert float NaN to integer` |
| 16 | `GET /api/geotiff/available-maps` | 200 | PASS | 72 maps, 4 return periods, 18 time steps |
| 17 | `GET /api/geotiff/flood-map?return_period=rr01&time_step=1` | 200 | PASS | Metadata with bounds, shape, CRS |
| 18 | `GET /api/geotiff/flood-depth?lat=14.6507&lon=121.1029&...` | 200 | PASS | flood_depth=0.0038, is_flooded=false |
| 19 | `GET /api/debug/hazard-cache` | 200 | PASS | 14 flood cache entries, 0 scout |
| 20 | `GET /api/debug/graph-risk-scores` | 200 | PASS | 35932 edges, max risk=0.211 |
| 21 | `GET /api/debug/simulation-events` | 200 | PASS | Simulation stopped, 0 events |

---

## Teammate 2: Routing & Evacuation (12 tests — 7 PASS, 4 FAIL, 1 retested)

| # | Endpoint | Method | HTTP | Result | Note |
|---|----------|--------|------|--------|------|
| 1 | `/api/route` | POST | 200 | PASS | 71 coords, distance=2182.7m, risk=0.0107 |
| 2 | `/api/route` | POST | 200 | PASS | Different route (68 coords), distance=3057.2m, risk=0.0 |
| 3 | `/api/route` (safest) | POST | 200 | PASS | risk=0.0107, includes explanation |
| 4 | `/api/route` (fastest) | POST | 200 | PASS | Identical to safest (low-risk area) |
| 5 | `/api/evacuation-center` (JSON obj) | POST | 422 | **FAIL** | Expects `Tuple[float,float]` body, not JSON object |
| 6 | `/api/evacuation-center` (array) | POST | 500 | **FAIL** | Array parses but handler crashes server-side |
| 7 | `/api/evacuation-center` (with query) | POST | 422 | **FAIL** | Same tuple parsing issue |
| 8 | `/api/route` (missing field) | POST | 422 | PASS | Correct: "Field required" |
| 9 | `/api/route` (empty body) | POST | 422 | PASS | Correct: both fields required |
| 10 | `/api/route` (outside Marikina) | POST | 400 | PASS | "Could not map coordinates to road network" |
| 11 | `/api/route` (same start/end) | POST | 200 | PASS | Single-point path, distance=0.0 |
| 12 | `/api/feedback` | POST | 500 | **FAIL** | Invalid feedback_type causes 500 not 422. Retested with valid values: PASS |

---

## Teammate 3: Orchestrator & MQ Missions (15 tests — 12 PASS, 2 FAIL, 1 WARN)

| # | Endpoint | Method | HTTP | Result | Note |
|---|----------|--------|------|--------|------|
| 1 | `/api/orchestrator/chat` (assess_risk) | POST | 200 | PASS | Correctly mapped to assess_risk |
| 2 | `/api/orchestrator/chat` (route) | POST | 200 | **FAIL** | LLM missed `end` coords, mission FAILED |
| 3 | `/api/orchestrator/chat` (evacuation) | POST | 200 | PASS | Geocoded Nangka correctly |
| 4 | `/api/orchestrator/chat` (cascade) | POST | 200 | PASS | Correctly identified cascade_risk_update |
| 5 | `/api/orchestrator/mission` (route) | POST | 200 | PASS | Mission created with route params |
| 6 | Poll route mission | GET | 200 | PASS | COMPLETED: 70 segments, 2182m, risk 0.0107 |
| 7 | `/api/orchestrator/mission` (risk) | POST | 200 | PASS | Created in AWAITING_SCOUT |
| 8 | Poll risk mission | GET | 200 | **WARN** | COMPLETED but with scout list/tuple + hazard tuple.lower() errors |
| 9 | `/api/orchestrator/missions` | GET | 200 | **FAIL** | Returns `[]` — completed missions not listed |
| 10 | `/api/orchestrator/mission/{id}/summary` | GET | 200 | PASS | LLM summary generated |
| 11 | Invalid mission type | POST | 200 | PASS | Correctly FAILED state |
| 12 | Fake mission ID | GET | 404 | PASS | Correct not-found response |
| 13 | Empty chat message | POST | 200 | WARN | No validation, LLM hallucinated |
| 14 | Concurrency: 3 missions fired | POST x3 | 200 | PASS | All got unique IDs |
| 15 | Concurrency: polling | GET x3 | 200 | PASS | All 3 completed independently |

---

## Teammate 4: Simulation, WebSocket & Admin (18 tests — 15 PASS, 3 FAIL)

| # | Endpoint | Method | HTTP | Result | Note |
|---|----------|--------|------|--------|------|
| 1 | `/api/simulation/status` | GET | 200 | PASS | Initial state="stopped", tick_count=0 |
| 2 | `/api/simulation/start` (light) | POST | 200 | PASS | Started in light mode |
| 3 | `/api/simulation/status` | GET | 200 | PASS | state="running", tick_count=1 |
| 4 | `/api/simulation/status` (5s later) | GET | 200 | PASS | tick_count=5 |
| 5 | `/api/simulation/stop` | POST | 200 | PASS | state="paused", tick preserved |
| 6 | `/api/simulation/status` (stopped) | GET | 200 | PASS | state="paused", is_paused=true |
| 7 | `/api/simulation/reset` | POST | 200 | PASS | Reset to stopped |
| 8 | `/api/simulation/status` (reset) | GET | 200 | PASS | state="stopped", tick_count=0 |
| 9 | `/api/admin/geotiff/status` | GET | 200 | PASS | geotiff_enabled=true, rr01/ts1 |
| 10 | `/api/admin/geotiff/set-scenario` (rr02/ts3) | POST | 500 | **FAIL** | Missing `collect_and_forward_data()` on FloodAgent |
| 11 | `/api/admin/geotiff/status` (verify) | GET | 200 | PASS | Scenario updated despite 500 |
| 12 | `/api/admin/geotiff/set-scenario` (reset) | POST | 500 | **FAIL** | Same missing method error |
| 13 | `/api/admin/collect-flood-data` | POST | 500 | **FAIL** | Same missing method error |
| 14 | `/api/agents/scout/collect` | POST | 200 | PASS | Skipped (simulation mode) |
| 15 | `/api/scheduler/trigger` | POST | 200 | PASS | 14 data points collected |
| 16 | WebSocket connect | WS | - | PASS | Connected successfully |
| 17 | WebSocket recv | WS | - | PASS | Received type="connection" |
| 18 | WebSocket ping/pong | WS | - | PASS | Ping/pong works |

---

## Observations

- **Routing core is solid** — all basic route calculations pass, error handling works well
- **Simulation lifecycle works end-to-end** — start/stop/reset/tick progression all correct
- **WebSocket works** — connect, receive, ping/pong all functional
- **Orchestrator FSM works** — missions progress through states and complete, concurrency is handled
- **LLM integration works** — NL interpretation + summaries functional, but edge cases exist
- **Graph loaded** — 16,877 nodes, 35,932 edges, 155 evacuation centers
- **FloodAgent refactor left stale references** — `collect_and_forward_data()` removed but still called from `main.py`
- **Evacuation center endpoints need fixes** — both the listing (NaN) and routing (crash) are broken
