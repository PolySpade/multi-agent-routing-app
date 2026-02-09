# Orchestrator Agent Implementation - Change Log

## Overview

Replaced the placeholder OrchestratorAgent with a real MAS-participating orchestrator
that coordinates multi-step workflows via MessageQueue and FIPA-ACL protocol.

**Date**: 2026-02-07
**Branch**: Indiv-Agents

---

## Summary of Changes

| # | File | Change Type | Description |
|---|------|-------------|-------------|
| 1 | `config/agents.yaml` | Added | `orchestrator_agent:` config section (timeouts, concurrency, retry) |
| 2 | `app/core/agent_config.py` | Added | `OrchestratorConfig` dataclass + `get_orchestrator_config()` method |
| 3 | `app/agents/orchestrator_agent.py` | Rewritten | Full MQ participant with mission FSM, timeout handling |
| 4 | `app/agents/hazard_agent.py` | Modified | Added `process_and_update` action + INFORM reply in REQUEST handler |
| 5 | `app/agents/scout_agent.py` | Modified | Added MQ request handling in `step()` for `scan_location` action |
| 6 | `app/agents/flood_agent.py` | Modified | Added MQ request handling in `step()` for `collect_data` action |
| 7 | `app/agents/routing_agent.py` | Modified | Added MQ support (`message_queue` param), handles `calculate_route` and `find_evacuation_center` |
| 8 | `app/agents/evacuation_manager_agent.py` | Modified | Added MQ request handling in `step()` for `handle_distress_call` |
| 9 | `app/main.py` | Modified | Register all agents with lifecycle manager, updated orchestrator endpoints |

---

## Detailed Changes

### 1. `config/agents.yaml` - Orchestrator Config Section

Added `orchestrator_agent:` section with:
- **Mission timeouts**: Per-mission-type timeouts (assess_risk=120s, route=30s, etc.)
- **Concurrency limits**: `max_concurrent_missions: 10`, `max_completed_history: 100`
- **Retry policy**: `max_retries: 2`, `retry_delay_seconds: 5.0`

### 2. `app/core/agent_config.py` - OrchestratorConfig

New `OrchestratorConfig` dataclass with fields:
- `default_timeout`, `assess_risk_timeout`, `evacuation_timeout`, `route_timeout`, `cascade_timeout`
- `max_concurrent_missions`, `max_completed_history`
- `max_retries`, `retry_delay_seconds`

New `get_orchestrator_config()` method on `AgentConfigLoader`.

### 3. `app/agents/orchestrator_agent.py` - Complete Rewrite

**Before**: Thin wrapper using direct `asyncio.to_thread(agent.method())` calls. No MQ usage, `step()` was a no-op.

**After**:
- **MQ Participant**: Registers with MessageQueue, polls in `step()`, sends/receives ACL messages
- **Mission State Machine**: `MissionState` enum with FSM transitions per mission type
- **Mission Types**:
  - `assess_risk`: PENDING -> AWAITING_SCOUT -> AWAITING_FLOOD -> AWAITING_HAZARD -> COMPLETED
  - `coordinated_evacuation`: PENDING -> AWAITING_EVACUATION -> COMPLETED
  - `route_calculation`: PENDING -> AWAITING_ROUTING -> COMPLETED
  - `cascade_risk_update`: PENDING -> AWAITING_FLOOD -> AWAITING_HAZARD -> COMPLETED
- **Timeout Handling**: Missions that exceed their deadline are auto-failed
- **Conversation Tracking**: Uses `conversation_id` to correlate REQUEST/INFORM pairs
- **Config-Driven**: Loads `OrchestratorConfig` from YAML

**Key methods**:
- `step()`: Polls MQ + checks timeouts (called by AgentLifecycleManager)
- `start_mission()`: Creates mission, kicks off FSM
- `get_mission_status()`: Returns mission state for polling
- `_advance_mission()`: Routes to per-type FSM handler
- `_send_request()`: Sends REQUEST via MQ to sub-agent by role

### 4. `app/agents/hazard_agent.py` - REQUEST Handler Update

- Added `process_and_update` action in `_handle_request_message()`
- Sends INFORM reply back to requester with `conversation_id` for correlation

### 5. `app/agents/scout_agent.py` - MQ Request Handling

- Added `_process_mq_requests()` called at start of `step()`
- Handles `scan_location` action: geocodes location, returns coordinates
- Sends INFORM reply to requester

### 6. `app/agents/flood_agent.py` - MQ Request Handling

- Added `_process_mq_requests()` called at start of `step()`
- Handles `collect_data` action: forces `collect_flood_data()` + sends to hazard
- Sends INFORM reply to requester with location count

### 7. `app/agents/routing_agent.py` - Full MQ Support

- Added `message_queue` parameter to `__init__`, registers with MQ
- Added `_process_mq_requests()` called in `step()`
- Handles `calculate_route` action: runs pathfinding, returns route
- Handles `find_evacuation_center` action: finds nearest center, returns result
- Sends INFORM reply to requester

### 8. `app/agents/evacuation_manager_agent.py` - MQ Request Handling

- Added `_process_mq_requests()` called at start of `step()`
- Handles `handle_distress_call` action: runs distress call handler
- Sends INFORM reply to requester

### 9. `app/main.py` - Lifecycle & Endpoints

- Passes `message_queue` to `RoutingAgent` constructor
- Registers ALL agents with `AgentLifecycleManager` (priority-ordered)
- Updated `POST /api/orchestrator/command` to use `start_mission()` (returns mission_id)
- Added `GET /api/orchestrator/mission/{mission_id}` for status polling
- Added `GET /api/orchestrator/missions` for listing active missions

---

## Architecture: Before vs After

### Before (Placeholder)
```
Frontend -> POST /api/orchestrator/command
         -> orchestrator.execute_mission()
         -> asyncio.to_thread(agent.method())  # Direct call
         -> return result synchronously
```

### After (Real MAS Orchestrator)
```
Frontend -> POST /api/orchestrator/mission
         -> orchestrator.start_mission()         # Creates FSM mission
         -> returns mission_id immediately

AgentLifecycleManager (1Hz tick loop):
  Tick N:   Orchestrator.step() -> sends REQUEST to scout via MQ
            Scout.step()        -> picks up REQUEST, replies INFORM
  Tick N+1: Orchestrator.step() -> picks up INFORM, sends REQUEST to flood
            Flood.step()        -> picks up REQUEST, replies INFORM
  Tick N+2: Orchestrator.step() -> picks up INFORM, sends REQUEST to hazard
            Hazard.step()       -> picks up REQUEST, replies INFORM
  Tick N+3: Orchestrator.step() -> picks up INFORM, mission COMPLETED

Frontend -> GET /api/orchestrator/mission/{id}  # Poll for result
```

---

## Mission State Machines

### assess_risk
```
PENDING ─── [has location?] ──► AWAITING_SCOUT ──► AWAITING_FLOOD ──► AWAITING_HAZARD ──► COMPLETED
        └── [no location] ─────────────────────────┘
```

### coordinated_evacuation
```
PENDING ──► AWAITING_EVACUATION ──► COMPLETED
```

### route_calculation
```
PENDING ──► AWAITING_ROUTING ──► COMPLETED
```

### cascade_risk_update
```
PENDING ──► AWAITING_FLOOD ──► AWAITING_HAZARD ──► COMPLETED
```

All missions can transition to FAILED or TIMED_OUT from any active state.

---

## LLM Brain Integration (2026-02-07)

### Changes

| # | File | Change Type | Description |
|---|------|-------------|-------------|
| 10 | `app/agents/orchestrator_agent.py` | Enhanced | Added LLM-powered `interpret_request()`, `summarize_mission()`, `chat_and_execute()` |
| 11 | `app/main.py` | Modified | Pass `get_llm_service()` to orchestrator, added `/api/orchestrator/chat` and `/api/orchestrator/mission/{id}/summary` endpoints |

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/orchestrator/chat` | Natural language interface - LLM interprets message and creates appropriate mission |
| GET | `/api/orchestrator/mission/{id}/summary` | LLM-generated human-readable summary of mission results |

### LLM Methods Added to OrchestratorAgent

- **`interpret_request(user_message)`**: Sends user message to LLM with a system prompt describing the 4 mission types and Marikina reference coordinates. LLM returns JSON with `mission_type`, `params`, and `reasoning`.
- **`summarize_mission(mission_id)`**: Sends mission results to LLM for a human-readable summary. Falls back to basic template if LLM is unavailable.
- **`chat_and_execute(user_message)`**: End-to-end: interpret -> fix params -> start mission.
- **`_fix_params(mission_type, params)`**: Fixes common LLM output issues (string coords, nested arrays, swapped start/end).
- **`_parse_llm_json(text)`**: Robust JSON parser that handles markdown code blocks, missing closing braces, and embedded JSON.

### Bug Fixes (2026-02-07)

- **evacuation_manager_agent.py**: Added MQ registration in `__init__` (was missing, caused `Agent not registered` error every tick)
- **orchestrator_agent.py**: Fixed `MissionState` serialization (`.value` instead of `str()` which produced `MissionState.COMPLETED` instead of `COMPLETED`)
- **scout_agent.py**: Changed noisy `INFO` logs to `DEBUG` (was logging "collecting simulated data" + "no simulation data" every second)

### Test Results (Real-time Verified)

| Mission Type | Chat Message | Result |
|---|---|---|
| `assess_risk` | "Check if Barangay Tumana is safe from flooding" | COMPLETED - Scout scanned coords, Flood collected 14 stations, Hazard updated 5500 edges |
| `route_calculation` | "Find me the safest route from Nangka to Industrial Valley" | COMPLETED - 4km route, 115 segments |
| `coordinated_evacuation` | "I need to evacuate from Malanday, the water is rising fast!" | COMPLETED - Routed to Fairlane Gym, 498m |
| `cascade_risk_update` | "Update all the flood data and recalculate risk" | COMPLETED - 14 locations, 5500 edges |
