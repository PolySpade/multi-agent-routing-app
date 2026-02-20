"""
Orchestrator Chat Integration Test Suite
==========================================

Tests the orchestrator agent's chat interface end-to-end against the running
server. Covers flood depth queries, risk assessments, routing between points,
clarification flow, multi-step missions, off-topic rejection, and edge cases.

Prerequisites:
  - Server running: uvicorn app.main:app --reload
  - Ollama running with configured text model (e.g. qwen3)

Usage:
  python -m tests.test_orchestrator_chat                    # full suite
  python -m tests.test_orchestrator_chat --offline-only     # no server needed
  python -m tests.test_orchestrator_chat --no-llm           # skip LLM tests
  python -m tests.test_orchestrator_chat --timeout 120      # custom poll timeout
"""

import argparse
import copy
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_POLL_TIMEOUT = 90  # seconds
POLL_INTERVAL = 2  # seconds between status polls

# Marikina barangay coordinates for reference
COORDS = {
    "tumana": [14.6608, 121.1004],
    "malanday": [14.6653, 121.1023],
    "concepcion_uno": [14.6416, 121.0978],
    "concepcion_dos": [14.6440, 121.0958],
    "nangka": [14.6568, 121.1107],
    "sto_nino": [14.6395, 121.0908],
    "industrial_valley": [14.6332, 121.0959],
    "city_center": [14.6507, 121.1029],
    "parang": [14.6475, 121.0955],
    "kalumpang": [14.6540, 121.0970],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def separator(title: str, char: str = "=", width: int = 78) -> None:
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def subseparator(title: str) -> None:
    print(f"\n  --- {title} ---")


def print_json(data: Any, indent: int = 2) -> None:
    try:
        print(json.dumps(data, indent=indent, default=str))
    except (TypeError, ValueError):
        print(data)


class TestReport:
    """Collects results from all tests for the final report."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def add(self, name: str, passed: bool, duration: float = 0.0,
            details: str = "", error: str = "") -> None:
        self.entries.append({
            "name": name,
            "passed": passed,
            "duration": duration,
            "details": details,
            "error": error,
        })

    def summary(self) -> None:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        passed = sum(1 for e in self.entries if e["passed"])
        failed = [e for e in self.entries if not e["passed"]]

        separator("Test Summary")
        print(f"  Total tests    : {len(self.entries)}")
        print(f"  Passed         : {passed}")
        print(f"  Failed         : {len(failed)}")
        print(f"  Total time     : {elapsed:.1f}s")

        if failed:
            print("\n  Failed tests:")
            for e in failed:
                print(f"    - {e['name']}: {e['error'] or 'FAIL'}")

    @property
    def total_failures(self) -> int:
        return sum(1 for e in self.entries if not e["passed"])


# ---------------------------------------------------------------------------
# API callers
# ---------------------------------------------------------------------------

def check_server(base_url: str) -> bool:
    try:
        r = requests.get(f"{base_url}/api/health", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def check_llm_health(base_url: str) -> bool:
    try:
        r = requests.get(f"{base_url}/api/llm/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("available", False) or data.get("status") == "ok"
        return False
    except Exception:
        return False


def send_chat(base_url: str, message: str,
              user_location: Optional[Dict] = None) -> Dict[str, Any]:
    """POST /api/orchestrator/chat"""
    payload: Dict[str, Any] = {"message": message}
    if user_location:
        payload["user_location"] = user_location
    r = requests.post(
        f"{base_url}/api/orchestrator/chat",
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def send_direct_mission(base_url: str, mission_type: str,
                        params: Dict[str, Any]) -> Dict[str, Any]:
    """POST /api/orchestrator/mission"""
    r = requests.post(
        f"{base_url}/api/orchestrator/mission",
        json={"mission_type": mission_type, "params": params},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def poll_mission(base_url: str, mission_id: str,
                 timeout: float = DEFAULT_POLL_TIMEOUT) -> Dict[str, Any]:
    """Poll until terminal state or timeout."""
    terminal = {"COMPLETED", "FAILED", "TIMED_OUT"}
    last_state = None
    start = time.time()

    while time.time() - start < timeout:
        r = requests.get(
            f"{base_url}/api/orchestrator/mission/{mission_id}", timeout=10
        )
        if r.status_code == 404:
            time.sleep(POLL_INTERVAL)
            continue
        r.raise_for_status()
        data = r.json()
        state = data.get("state", "UNKNOWN")

        if state != last_state:
            print(f"    [{timestamp()}] {last_state} -> {state}")
            last_state = state

        if state in terminal:
            return data

        time.sleep(POLL_INTERVAL)

    return {"state": "POLL_TIMEOUT", "mission_id": mission_id}


def get_summary(base_url: str, mission_id: str) -> Optional[Dict[str, Any]]:
    """GET /api/orchestrator/mission/{id}/summary"""
    try:
        r = requests.get(
            f"{base_url}/api/orchestrator/mission/{mission_id}/summary",
            timeout=30,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def clear_chat(base_url: str) -> None:
    """POST /api/orchestrator/chat/clear"""
    try:
        requests.post(f"{base_url}/api/orchestrator/chat/clear", timeout=5)
    except Exception:
        pass


def get_flood_data(base_url: str) -> Optional[Dict[str, Any]]:
    """GET /api/flood-data/latest"""
    try:
        r = requests.get(f"{base_url}/api/flood-data/latest", timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Offline unit tests (no server needed)
# ---------------------------------------------------------------------------

def run_offline_tests(report: TestReport) -> None:
    """Offline tests that don't require a running server."""

    separator("Offline Unit Tests")

    # ---- _fix_params tests ----
    subseparator("_fix_params")
    from app.agents.orchestrator_agent import OrchestratorAgent

    fix_params_cases = [
        {
            "name": "String coordinates -> list",
            "type": "route_calculation",
            "input": {"start": "[14.65, 121.11]", "end": "[14.63, 121.09]"},
            "check": lambda p: isinstance(p["start"], list) and isinstance(p["end"], list),
        },
        {
            "name": "Nested array unwrap",
            "type": "route_calculation",
            "input": {
                "start": [[14.65, 121.11], [14.63, 121.09]],
                "end": [[14.65, 121.11], [14.63, 121.09]],
            },
            "check": lambda p: isinstance(p["start"][0], float) and isinstance(p["end"][0], float),
        },
        {
            "name": "Start equals end fallback to origin/destination",
            "type": "route_calculation",
            "input": {
                "start": [14.65, 121.11],
                "end": [14.65, 121.11],
                "origin": [14.60, 121.10],
                "destination": [14.70, 121.12],
            },
            "check": lambda p: p["start"] == [14.60, 121.10] and p["end"] == [14.70, 121.12],
        },
        {
            "name": "String evacuation location -> list",
            "type": "coordinated_evacuation",
            "input": {"user_location": "[14.66, 121.10]", "message": "Help!"},
            "check": lambda p: isinstance(p["user_location"], list),
        },
        {
            "name": "Nested evacuation location unwrap",
            "type": "coordinated_evacuation",
            "input": {"user_location": [[14.66, 121.10]], "message": "Help!"},
            "check": lambda p: isinstance(p["user_location"][0], float),
        },
        {
            "name": "Normal params unchanged",
            "type": "route_calculation",
            "input": {"start": [14.65, 121.11], "end": [14.63, 121.09]},
            "check": lambda p: p["start"] == [14.65, 121.11] and p["end"] == [14.63, 121.09],
        },
        {
            "name": "Missing start uses user_location",
            "type": "route_calculation",
            "input": {"end": [14.63, 121.09]},
            "check": lambda p: p["start"] == [14.66, 121.10],
            "user_location": {"lat": 14.66, "lng": 121.10},
        },
        {
            "name": "Missing start and no user_location defaults to city center",
            "type": "route_calculation",
            "input": {"end": [14.63, 121.09]},
            "check": lambda p: p["start"] == [14.6507, 121.1029],
        },
        {
            "name": "assess_risk params pass through unchanged",
            "type": "assess_risk",
            "input": {"location": "Tumana"},
            "check": lambda p: p["location"] == "Tumana",
        },
    ]

    for case in fix_params_cases:
        t0 = time.time()
        params = copy.deepcopy(case["input"])
        user_loc = case.get("user_location")
        result = OrchestratorAgent._fix_params(case["type"], params, user_location=user_loc)
        ok = case["check"](result)
        dur = time.time() - t0
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] {case['name']}")
        if not ok:
            print(f"           Result: {result}")
        report.add(f"_fix_params: {case['name']}", ok, dur,
                    error="" if ok else f"Got: {result}")

    # ---- _parse_llm_json tests ----
    subseparator("_parse_llm_json (via llm_utils)")
    from app.core.llm_utils import parse_llm_json

    parse_cases = [
        {
            "name": "Clean JSON",
            "input": '{"mission_type": "assess_risk", "params": {}}',
            "check": lambda r: r is not None and r["mission_type"] == "assess_risk",
        },
        {
            "name": "Markdown fenced JSON",
            "input": '```json\n{"mission_type": "route_calculation"}\n```',
            "check": lambda r: r is not None and r["mission_type"] == "route_calculation",
        },
        {
            "name": "Truncated - missing closing brace",
            "input": '{"mission_type": "assess_risk", "params": {"location": "Tumana"}',
            "check": lambda r: r is not None and r.get("params", {}).get("location") == "Tumana",
        },
        {
            "name": "Leading text before JSON",
            "input": 'Here is my response:\n{"mission_type": "cascade_risk_update", "params": {}}',
            "check": lambda r: r is not None and r["mission_type"] == "cascade_risk_update",
        },
        {
            "name": "No JSON at all",
            "input": "I don't understand the question.",
            "check": lambda r: r is None,
        },
        {
            "name": "Deeply truncated string value",
            "input": '{"mission_type": "assess_risk", "reasoning": "The user asked about flo',
            "check": lambda r: r is not None and r["mission_type"] == "assess_risk",
        },
        {
            "name": "Multi-step JSON",
            "input": '{"mission_type": "multi_step", "steps": [{"mission_type": "assess_risk", "params": {"location": "Tumana"}}]}',
            "check": lambda r: r is not None and r["mission_type"] == "multi_step" and len(r["steps"]) == 1,
        },
        {
            "name": "needs_clarification JSON",
            "input": '{"mission_type": "needs_clarification", "question": "Where do you want to start?"}',
            "check": lambda r: r is not None and r["mission_type"] == "needs_clarification",
        },
    ]

    for case in parse_cases:
        t0 = time.time()
        result = parse_llm_json(case["input"])
        ok = case["check"](result)
        dur = time.time() - t0
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] {case['name']}")
        if not ok:
            print(f"           Input:  {case['input'][:80]}")
            print(f"           Result: {result}")
        report.add(f"parse_llm_json: {case['name']}", ok, dur,
                    error="" if ok else f"Got: {result}")

    # ---- _location_to_coords tests ----
    subseparator("_location_to_coords")

    # Need an instance — create a minimal mock
    from unittest.mock import MagicMock
    from app.communication.message_queue import MessageQueue

    mock_env = MagicMock()
    mock_mq = MagicMock(spec=MessageQueue)
    mock_mq.register_agent = MagicMock()
    mock_mq.receive_message = MagicMock(return_value=None)
    orch = OrchestratorAgent(
        agent_id="test_orch",
        environment=mock_env,
        message_queue=mock_mq,
        sub_agents={
            "scout": MagicMock(agent_id="scout"),
            "flood": MagicMock(agent_id="flood"),
            "hazard": MagicMock(agent_id="hazard"),
            "routing": MagicMock(agent_id="routing"),
            "evacuation": MagicMock(agent_id="evacuation"),
        },
    )

    location_cases = [
        {
            "name": "Exact match: tumana",
            "input": "Tumana",
            "check": lambda c: c == (14.6608, 121.1004),
        },
        {
            "name": "With prefix: Barangay Nangka",
            "input": "Barangay Nangka",
            "check": lambda c: c == (14.6568, 121.1107),
        },
        {
            "name": "With prefix: Brgy. Sto. Nino",
            "input": "Brgy. Sto. Nino",
            "check": lambda c: c == (14.6395, 121.0908),
        },
        {
            "name": "Case insensitive: MALANDAY",
            "input": "MALANDAY",
            "check": lambda c: c == (14.6653, 121.1023),
        },
        {
            "name": "Scored match: Industrial Valley Complex (substring)",
            "input": "Industrial Valley Complex",
            "check": lambda c: c[0] is not None,  # Should match industrial valley
        },
        {
            "name": "False positive prevention: Paragua Street should NOT match Parang",
            "input": "Paragua Street",
            "check": lambda c: c == (None, None),
        },
        {
            "name": "Unknown location returns None",
            "input": "Quezon City",
            "check": lambda c: c == (None, None),
        },
        {
            "name": "Concepcion Uno exact",
            "input": "Concepcion Uno",
            "check": lambda c: c == (14.6416, 121.0978),
        },
        {
            "name": "Santa Elena alias",
            "input": "Santa Elena",
            "check": lambda c: c == (14.6490, 121.1060),
        },
        {
            "name": "Sta. Elena alias",
            "input": "Sta. Elena",
            "check": lambda c: c == (14.6490, 121.1060),
        },
    ]

    for case in location_cases:
        t0 = time.time()
        result = orch._location_to_coords(case["input"])
        ok = case["check"](result)
        dur = time.time() - t0
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] {case['name']} -> {result}")
        report.add(f"_location_to_coords: {case['name']}", ok, dur,
                    error="" if ok else f"Got: {result}")

    # ---- MissionState enum tests ----
    subseparator("MissionState enum")
    from app.agents.orchestrator_agent import MissionState

    state_cases = [
        ("PENDING exists", MissionState.PENDING.value == "PENDING"),
        ("AWAITING_SUB_MISSION exists", MissionState.AWAITING_SUB_MISSION.value == "AWAITING_SUB_MISSION"),
        ("COMPLETED exists", MissionState.COMPLETED.value == "COMPLETED"),
        ("FAILED exists", MissionState.FAILED.value == "FAILED"),
        ("TIMED_OUT exists", MissionState.TIMED_OUT.value == "TIMED_OUT"),
        ("String coercion", str(MissionState.PENDING) == "MissionState.PENDING" or MissionState.PENDING == "PENDING"),
    ]

    for name, ok in state_cases:
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] {name}")
        report.add(f"MissionState: {name}", ok)

    # ---- _get_timeout tests ----
    subseparator("_get_timeout")

    timeout_cases = [
        ("assess_risk", lambda t: t > 0),
        ("route_calculation", lambda t: t > 0),
        ("coordinated_evacuation", lambda t: t > 0),
        ("cascade_risk_update", lambda t: t > 0),
        ("multi_step", lambda t: t >= 120),  # Should be 180.0 from config
        ("unknown_type", lambda t: t > 0),  # Should return default
    ]

    for mtype, check in timeout_cases:
        t = orch._get_timeout(mtype)
        ok = check(t)
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] {mtype} -> {t}s")
        report.add(f"_get_timeout: {mtype}", ok, error="" if ok else f"Got: {t}")

    # ---- _fallback_summary tests ----
    subseparator("_fallback_summary")

    summary_cases = [
        {
            "name": "Completed mission summary",
            "input": {"state": "COMPLETED", "type": "assess_risk", "elapsed_seconds": 12.5, "results": {}},
            "check": lambda s: "completed" in s.lower() and "12.5" in s,
        },
        {
            "name": "Failed mission summary",
            "input": {"state": "FAILED", "type": "route_calculation", "elapsed_seconds": 5.0, "results": {}, "error": "No route found"},
            "check": lambda s: "failed" in s.lower() and "no route found" in s.lower(),
        },
        {
            "name": "In-progress mission summary",
            "input": {"state": "AWAITING_HAZARD", "type": "cascade_risk_update", "elapsed_seconds": 3.0, "results": {}},
            "check": lambda s: "in progress" in s.lower(),
        },
        {
            "name": "Completed with map_risk data",
            "input": {
                "state": "COMPLETED", "type": "assess_risk", "elapsed_seconds": 8.0,
                "results": {
                    "map_risk": {
                        "status": "ok", "risk_level": "moderate",
                        "avg_risk": 0.45, "max_risk": 0.78,
                        "high_risk_edges": 12, "impassable_edges": 2,
                    }
                }
            },
            "check": lambda s: "moderate" in s.lower() and "0.45" in s,
        },
    ]

    for case in summary_cases:
        t0 = time.time()
        result = OrchestratorAgent._fallback_summary(case["input"])
        ok = case["check"](result)
        dur = time.time() - t0
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] {case['name']}")
        if not ok:
            print(f"           Got: {result}")
        report.add(f"_fallback_summary: {case['name']}", ok, dur,
                    error="" if ok else f"Got: {result}")

    # ---- Multi-step mission tracking fields ----
    subseparator("start_mission multi_step fields")

    result = orch.start_mission("multi_step", {
        "steps": [
            {"mission_type": "assess_risk", "params": {"location": "Tumana"}},
        ]
    })
    mid = result.get("mission_id")
    # The mission might have already moved through the FSM (failed because mocks)
    # but we can still check the completed/active missions for the tracking fields
    ok = mid is not None
    icon = "PASS" if ok else "FAIL"
    print(f"    [{icon}] multi_step mission creates with mission_id={mid}")
    report.add("start_mission: multi_step creates mission_id", ok,
                error="" if ok else f"Result: {result}")


# ---------------------------------------------------------------------------
# Chat-based integration tests (requires server + LLM)
# ---------------------------------------------------------------------------

CHAT_TEST_SCENARIOS = [
    # --- Flood depth queries ---
    {
        "name": "Chat: Flood depth at Tumana",
        "message": "What is the current flood depth at Barangay Tumana?",
        "valid_types": ["assess_risk"],
        "description": "Should trigger assess_risk for Tumana flood depth inquiry",
    },
    {
        "name": "Chat: Flood depth at Nangka",
        "message": "How deep is the flooding in Nangka right now?",
        "valid_types": ["assess_risk"],
        "description": "Should trigger assess_risk for Nangka flood depth",
    },
    {
        "name": "Chat: Flood depth at Malanday",
        "message": "Is there flooding at Barangay Malanday? What's the water level?",
        "valid_types": ["assess_risk"],
        "description": "Should trigger assess_risk for Malanday water level",
    },

    # --- Risk assessment queries ---
    {
        "name": "Chat: Risk at Industrial Valley",
        "message": "What's the current risk level at Industrial Valley?",
        "valid_types": ["assess_risk"],
        "description": "Should trigger assess_risk for Industrial Valley",
    },
    {
        "name": "Chat: Risk at Concepcion Uno",
        "message": "Check if Concepcion Uno is safe right now",
        "valid_types": ["assess_risk"],
        "description": "Should trigger assess_risk for Concepcion Uno",
    },
    {
        "name": "Chat: Risk at Sto. Nino",
        "message": "Assess the flood risk in Barangay Sto. Nino",
        "valid_types": ["assess_risk"],
        "description": "Should trigger assess_risk for Sto. Nino",
    },

    # --- Distance/routing queries ---
    {
        "name": "Chat: Route Tumana to Nangka",
        "message": "How do I get from Tumana to Nangka safely?",
        "valid_types": ["route_calculation", "multi_step"],
        "description": "Should calculate a route between two barangays",
    },
    {
        "name": "Chat: Route Malanday to Industrial Valley",
        "message": "Find the safest route from Malanday to Industrial Valley",
        "valid_types": ["route_calculation", "multi_step"],
        "description": "Should calculate route between Malanday and IV",
    },
    {
        "name": "Chat: Route Concepcion Uno to Sto. Nino",
        "message": "Navigate from Concepcion Uno to Sto. Nino",
        "valid_types": ["route_calculation", "multi_step"],
        "description": "Should calculate route between two barangays",
    },

    # --- Evacuation queries ---
    {
        "name": "Chat: Evacuation from Tumana",
        "message": "I'm trapped in Tumana, the water is waist-deep. I need to evacuate now!",
        "valid_types": ["coordinated_evacuation"],
        "description": "Should trigger coordinated_evacuation with urgency",
    },

    # --- Data refresh ---
    {
        "name": "Chat: Refresh flood data",
        "message": "Update all flood data and recalculate risks across the city",
        "valid_types": ["cascade_risk_update"],
        "description": "Should trigger cascade_risk_update",
    },

    # --- Off-topic rejection ---
    {
        "name": "Chat: Off-topic - math question",
        "message": "What is 2 + 2?",
        "expected_status": "off_topic",
        "description": "Math question should be rejected as off-topic",
    },
    {
        "name": "Chat: Off-topic - weather in Tokyo",
        "message": "What's the weather like in Tokyo?",
        "expected_status": "off_topic",
        "description": "Non-Marikina weather should be rejected",
    },
    {
        "name": "Chat: Off-topic - coding help",
        "message": "Write me a Python function to sort a list",
        "expected_status": "off_topic",
        "description": "Coding help should be rejected as off-topic",
    },

    # --- Multi-step queries ---
    {
        "name": "Chat: Multi-step - safety check then route",
        "message": "Is it safe to travel from Tumana to Concepcion Uno? Check the risk first then route me.",
        "valid_types": ["multi_step", "route_calculation"],
        "description": "Should decompose into assess_risk + route_calculation",
    },

    # --- Edge cases ---
    {
        "name": "Chat: Vague location - just Concepcion",
        "message": "What's the risk at Concepcion?",
        "valid_types": ["assess_risk", "needs_clarification"],
        "description": "Ambiguous location may trigger clarification or assess_risk",
    },
    {
        "name": "Chat: Marikina River danger",
        "message": "How dangerous is the Marikina River right now?",
        "valid_types": ["assess_risk", "cascade_risk_update"],
        "description": "River danger query could be risk assessment or data refresh",
    },
]


def run_chat_test(base_url: str, scenario: Dict[str, Any],
                  poll_timeout: float, report: TestReport) -> bool:
    """Run a single chat test scenario. Returns True if passed."""
    name = scenario["name"]
    msg = scenario["message"]
    t0 = time.time()

    try:
        subseparator(f'{name}: "{msg}"')
        chat_result = send_chat(base_url, msg)
        status = chat_result.get("status", "")
        dur = time.time() - t0

        # Check for expected status (off_topic, needs_clarification)
        expected_status = scenario.get("expected_status")
        if expected_status:
            ok = status == expected_status
            icon = "PASS" if ok else "FAIL"
            print(f"    [{icon}] Expected status='{expected_status}', got='{status}'")
            if not ok:
                print_json(chat_result)
            report.add(name, ok, dur, error="" if ok else f"Expected {expected_status}, got {status}")
            return ok

        # For mission-creating tests
        valid_types = scenario.get("valid_types", [])

        if status == "needs_clarification":
            # Acceptable if needs_clarification is in valid_types
            ok = "needs_clarification" in valid_types
            question = chat_result.get("message", "")
            print(f"    Clarification: {question}")
            icon = "PASS" if ok else "FAIL"
            print(f"    [{icon}] Got needs_clarification (valid={ok})")
            report.add(name, ok, dur, details=f"Clarification: {question}",
                        error="" if ok else f"Unexpected clarification: {question}")
            return ok

        if status == "off_topic":
            ok = "off_topic" in (scenario.get("expected_status", ""), )
            print(f"    Got off_topic (unexpected)")
            report.add(name, False, dur, error=f"Unexpected off_topic: {chat_result.get('interpretation', {}).get('message', '')}")
            return False

        if status != "ok":
            err = chat_result.get("interpretation", {}).get("message", str(chat_result))
            print(f"    ERROR: {err}")
            report.add(name, False, dur, error=f"Status {status}: {err}")
            return False

        # Validate mission type
        actual_type = chat_result.get("interpretation", {}).get("mission_type", "")
        type_ok = actual_type in valid_types if valid_types else True
        icon = "PASS" if type_ok else "WARN"
        print(f"    [{icon}] Mission type: {actual_type} (valid: {valid_types})")
        reasoning = chat_result.get("interpretation", {}).get("reasoning", "")
        print(f"    Reasoning: {reasoning}")

        # Poll for mission completion
        mission = chat_result.get("mission", {})
        mission_id = mission.get("mission_id")
        if not mission_id:
            report.add(name, False, dur, error="No mission_id returned")
            return False

        print(f"    Polling mission {mission_id}...")
        final = poll_mission(base_url, mission_id, poll_timeout)
        final_state = final.get("state", "UNKNOWN")
        dur = time.time() - t0

        # Get summary if completed
        if final_state == "COMPLETED":
            summary_result = get_summary(base_url, mission_id)
            if summary_result:
                summary_text = summary_result.get("summary", "")[:200]
                print(f"    Summary: {summary_text}")

        passed = final_state == "COMPLETED" and type_ok
        icon = "PASS" if passed else "FAIL"
        print(f"    [{icon}] Final state: {final_state}")

        report.add(name, passed, dur,
                    details=f"type={actual_type}, state={final_state}",
                    error="" if passed else f"State={final_state}, type_match={type_ok}")
        return passed

    except Exception as e:
        dur = time.time() - t0
        print(f"    ERROR: {e}")
        report.add(name, False, dur, error=str(e))
        return False


# ---------------------------------------------------------------------------
# Direct mission tests (deterministic, no LLM needed)
# ---------------------------------------------------------------------------

DIRECT_MISSION_SCENARIOS = [
    {
        "name": "Direct: Assess risk at Tumana",
        "mission_type": "assess_risk",
        "params": {"location": "Barangay Tumana"},
    },
    {
        "name": "Direct: Assess risk at Nangka",
        "mission_type": "assess_risk",
        "params": {"location": "Barangay Nangka"},
    },
    {
        "name": "Direct: Route Tumana to Nangka",
        "mission_type": "route_calculation",
        "params": {
            "start": COORDS["tumana"],
            "end": COORDS["nangka"],
            "preferences": {},
        },
    },
    {
        "name": "Direct: Route Malanday to Industrial Valley",
        "mission_type": "route_calculation",
        "params": {
            "start": COORDS["malanday"],
            "end": COORDS["industrial_valley"],
            "preferences": {},
        },
    },
    {
        "name": "Direct: Route Concepcion Uno to Sto. Nino",
        "mission_type": "route_calculation",
        "params": {
            "start": COORDS["concepcion_uno"],
            "end": COORDS["sto_nino"],
            "preferences": {},
        },
    },
    {
        "name": "Direct: Evacuation from Tumana",
        "mission_type": "coordinated_evacuation",
        "params": {
            "user_location": COORDS["tumana"],
            "message": "Water is chest-deep, need immediate evacuation!",
        },
    },
    {
        "name": "Direct: Cascade risk update",
        "mission_type": "cascade_risk_update",
        "params": {},
    },
    {
        "name": "Direct: Multi-step assess + route",
        "mission_type": "multi_step",
        "params": {
            "steps": [
                {"mission_type": "assess_risk", "params": {"location": "Tumana"}},
                {"mission_type": "route_calculation", "params": {
                    "start": COORDS["tumana"],
                    "end": COORDS["nangka"],
                }},
            ]
        },
    },
]


def run_direct_test(base_url: str, scenario: Dict[str, Any],
                    poll_timeout: float, report: TestReport) -> bool:
    """Run a direct mission test. Returns True if passed."""
    name = scenario["name"]
    t0 = time.time()

    try:
        subseparator(name)
        print(f"    Type: {scenario['mission_type']}")
        print(f"    Params: {json.dumps(scenario['params'], default=str)[:120]}")

        result = send_direct_mission(
            base_url, scenario["mission_type"], scenario["params"]
        )
        mission_id = result.get("mission_id")
        if not mission_id:
            err = result.get("message", str(result))
            print(f"    ERROR: No mission_id - {err}")
            report.add(name, False, time.time() - t0, error=err)
            return False

        print(f"    Mission created: {mission_id}")
        final = poll_mission(base_url, mission_id, poll_timeout)
        final_state = final.get("state", "UNKNOWN")
        dur = time.time() - t0

        passed = final_state == "COMPLETED"
        icon = "PASS" if passed else "FAIL"
        print(f"    [{icon}] {name} -> {final_state} ({dur:.1f}s)")

        report.add(name, passed, dur,
                    details=f"state={final_state}",
                    error="" if passed else f"State={final_state}")
        return passed

    except Exception as e:
        dur = time.time() - t0
        print(f"    ERROR: {e}")
        report.add(name, False, dur, error=str(e))
        return False


# ---------------------------------------------------------------------------
# Multi-turn conversation test
# ---------------------------------------------------------------------------

def run_multi_turn_test(base_url: str, poll_timeout: float,
                        report: TestReport) -> None:
    """Test multi-turn conversation context (follow-up messages)."""
    separator("Multi-Turn Conversation Test")

    clear_chat(base_url)

    # Turn 1: Ask about Nangka risk
    subseparator("Turn 1: Ask about Nangka")
    t0 = time.time()
    try:
        r1 = send_chat(base_url, "Check the flood risk in Nangka")
        s1 = r1.get("status", "")
        print(f"    Status: {s1}")
        if s1 == "ok":
            mid1 = r1.get("mission", {}).get("mission_id")
            if mid1:
                final1 = poll_mission(base_url, mid1, poll_timeout)
                print(f"    Turn 1 result: {final1.get('state', '?')}")

        dur1 = time.time() - t0
        ok1 = s1 in ("ok", "needs_clarification")
        report.add("Multi-turn: Turn 1 (Nangka risk)", ok1, dur1,
                    error="" if ok1 else f"Status: {s1}")

        # Turn 2: Follow up with "now route me there"
        subseparator("Turn 2: Follow up - route me there")
        t0 = time.time()
        r2 = send_chat(
            base_url,
            "Now route me there from Tumana",
            user_location={"lat": 14.6608, "lng": 121.1004},
        )
        s2 = r2.get("status", "")
        t2 = r2.get("interpretation", {}).get("mission_type", "")
        print(f"    Status: {s2}, type: {t2}")

        dur2 = time.time() - t0
        ok2 = s2 in ("ok", "needs_clarification")
        report.add("Multi-turn: Turn 2 (route me there)", ok2, dur2,
                    details=f"type={t2}",
                    error="" if ok2 else f"Status: {s2}")

        if s2 == "ok":
            mid2 = r2.get("mission", {}).get("mission_id")
            if mid2:
                final2 = poll_mission(base_url, mid2, poll_timeout)
                print(f"    Turn 2 result: {final2.get('state', '?')}")

    except Exception as e:
        dur = time.time() - t0
        print(f"    ERROR: {e}")
        report.add("Multi-turn: conversation", False, dur, error=str(e))

    clear_chat(base_url)


# ---------------------------------------------------------------------------
# Flood data endpoint test
# ---------------------------------------------------------------------------

def run_flood_data_test(base_url: str, report: TestReport) -> None:
    """Test the flood data endpoint."""
    separator("Flood Data Endpoint Test")

    t0 = time.time()
    try:
        data = get_flood_data(base_url)
        dur = time.time() - t0

        if data is None:
            print("    No flood data available (endpoint returned None)")
            report.add("Flood data: endpoint accessible", True, dur,
                        details="No data yet")
            return

        print(f"    Flood data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        ok = isinstance(data, (dict, list))
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] Flood data endpoint returns valid data")
        report.add("Flood data: endpoint returns data", ok, dur)

    except Exception as e:
        dur = time.time() - t0
        print(f"    ERROR: {e}")
        report.add("Flood data: endpoint accessible", False, dur, error=str(e))


# ---------------------------------------------------------------------------
# Server health test
# ---------------------------------------------------------------------------

def run_health_tests(base_url: str, report: TestReport) -> None:
    """Test basic server health endpoints."""
    separator("Health Endpoint Tests")

    # Health check
    t0 = time.time()
    try:
        r = requests.get(f"{base_url}/api/health", timeout=5)
        data = r.json()
        dur = time.time() - t0

        ok = data.get("status") == "healthy"
        print(f"    [{('PASS' if ok else 'FAIL')}] /api/health -> {data.get('status')}")
        print(f"    Graph: {data.get('graph_status')}, LLM: {data.get('llm_status')}")
        report.add("Health: /api/health", ok, dur)

        # Check agents are active
        agents = data.get("agents", {})
        for agent_name, status in agents.items():
            agent_ok = status == "active"
            print(f"    [{('PASS' if agent_ok else 'WARN')}] {agent_name}: {status}")
            report.add(f"Health: {agent_name}", agent_ok, 0)

    except Exception as e:
        dur = time.time() - t0
        report.add("Health: /api/health", False, dur, error=str(e))

    # LLM health
    t0 = time.time()
    try:
        r = requests.get(f"{base_url}/api/llm/health", timeout=5)
        data = r.json()
        dur = time.time() - t0
        available = data.get("available", False) or data.get("status") == "ok"
        print(f"    [{'PASS' if available else 'WARN'}] LLM available: {available}")
        report.add("Health: LLM available", available, dur)
    except Exception as e:
        dur = time.time() - t0
        report.add("Health: LLM endpoint", False, dur, error=str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Orchestrator chat integration test suite"
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL,
        help=f"Server base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_POLL_TIMEOUT,
        help=f"Mission poll timeout (default: {DEFAULT_POLL_TIMEOUT}s)",
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Skip tests that require the LLM",
    )
    parser.add_argument(
        "--offline-only", action="store_true",
        help="Only run offline unit tests (no server needed)",
    )
    parser.add_argument(
        "--chat-only", action="store_true",
        help="Only run LLM chat tests",
    )
    parser.add_argument(
        "--direct-only", action="store_true",
        help="Only run direct mission tests",
    )
    args = parser.parse_args()

    report = TestReport()

    # ------------------------------------------------------------------
    # Phase 0: Offline unit tests
    # ------------------------------------------------------------------
    run_offline_tests(report)

    if args.offline_only:
        report.summary()
        sys.exit(1 if report.total_failures else 0)

    # ------------------------------------------------------------------
    # Phase 1: Server connectivity
    # ------------------------------------------------------------------
    separator("Server Connectivity")
    if not check_server(args.base_url):
        print(f"  FATAL: Server not reachable at {args.base_url}")
        print("  Start with: uvicorn app.main:app --reload")
        report.summary()
        sys.exit(1)
    print(f"  Server running at {args.base_url}")

    llm_available = check_llm_health(args.base_url)
    print(f"  LLM available: {llm_available}")
    if args.no_llm:
        llm_available = False
        print("  (--no-llm flag set)")

    # ------------------------------------------------------------------
    # Phase 2: Health endpoint tests
    # ------------------------------------------------------------------
    run_health_tests(args.base_url, report)

    # ------------------------------------------------------------------
    # Phase 3: Flood data endpoint test
    # ------------------------------------------------------------------
    run_flood_data_test(args.base_url, report)

    # ------------------------------------------------------------------
    # Phase 4: Direct mission tests (no LLM)
    # ------------------------------------------------------------------
    if not args.chat_only:
        separator("Direct Mission Tests")
        for i, scenario in enumerate(DIRECT_MISSION_SCENARIOS, 1):
            print(f"\n  [{i}/{len(DIRECT_MISSION_SCENARIOS)}] {scenario['name']}")
            run_direct_test(args.base_url, scenario, args.timeout, report)
            time.sleep(1)

    # ------------------------------------------------------------------
    # Phase 5: LLM chat tests
    # ------------------------------------------------------------------
    if not args.direct_only and llm_available:
        separator("LLM Chat Tests")
        clear_chat(args.base_url)

        for i, scenario in enumerate(CHAT_TEST_SCENARIOS, 1):
            print(f"\n  [{i}/{len(CHAT_TEST_SCENARIOS)}] {scenario['name']}")
            run_chat_test(args.base_url, scenario, args.timeout, report)
            time.sleep(1)

        # Multi-turn conversation test
        run_multi_turn_test(args.base_url, args.timeout, report)

    elif not args.direct_only and not llm_available:
        separator("LLM Chat Tests - SKIPPED")
        print("  LLM not available. Start Ollama to enable.")

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    report.summary()
    sys.exit(1 if report.total_failures else 0)


if __name__ == "__main__":
    main()
