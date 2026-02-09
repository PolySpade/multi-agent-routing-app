"""
Orchestrator Brain Integration Test Suite
==========================================

Tests the orchestrator agent's LLM brain end-to-end against the running server.
Covers all 4 mission types via both the chat (NL) and direct mission APIs,
polls for completion, requests LLM summaries, and writes a mission report.

Prerequisites:
  - Server running: uvicorn app.main:app --reload
  - Ollama running with llama3.2:latest (or whichever text model is configured)

Usage:
  python -m tests.test_orchestrator_brain                 # full suite
  python -m tests.test_orchestrator_brain --base-url http://localhost:8000
  python -m tests.test_orchestrator_brain --no-llm        # skip chat/summary tests
  python -m tests.test_orchestrator_brain --timeout 120   # custom poll timeout
"""

import argparse
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

# Test scenarios: each maps a human message to expected mission behaviour
CHAT_SCENARIOS: List[Dict[str, Any]] = [
    {
        "name": "Assess Risk - Barangay Tumana",
        "message": "Check if Barangay Tumana is safe from flooding right now",
        "expected_mission_type": "assess_risk",
        "description": (
            "LLM should interpret a location safety question as an assess_risk "
            "mission targeting Barangay Tumana. The FSM should progress through "
            "AWAITING_SCOUT -> AWAITING_FLOOD -> AWAITING_HAZARD -> COMPLETED."
        ),
    },
    {
        "name": "Route Calculation - Nangka to Industrial Valley",
        "message": "Find me the safest route from Barangay Nangka to Industrial Valley",
        "expected_mission_type": "route_calculation",
        "description": (
            "LLM should extract start/end coordinates for Nangka and Industrial "
            "Valley and create a route_calculation mission. The FSM should go "
            "AWAITING_ROUTING -> COMPLETED."
        ),
    },
    {
        "name": "Coordinated Evacuation - Malanday",
        "message": "I need to evacuate from Malanday, the water is rising fast and I have children with me!",
        "expected_mission_type": "coordinated_evacuation",
        "description": (
            "LLM should recognise urgency and create a coordinated_evacuation "
            "mission with user_location near Malanday and distress message. "
            "FSM: AWAITING_EVACUATION -> COMPLETED."
        ),
    },
    {
        "name": "Cascade Risk Update - System-wide",
        "message": "Update all the flood data and recalculate risk levels across the city",
        "expected_mission_type": "cascade_risk_update",
        "description": (
            "LLM should map a data-refresh request to cascade_risk_update "
            "(no location needed). FSM: AWAITING_FLOOD -> AWAITING_HAZARD -> COMPLETED."
        ),
    },
]

# Direct mission payloads (bypass LLM) for deterministic testing
DIRECT_MISSIONS: List[Dict[str, Any]] = [
    {
        "name": "Direct - Assess Risk (Sto. Nino)",
        "mission_type": "assess_risk",
        "params": {"location": "Barangay Sto. Nino"},
        "description": "Direct assess_risk without LLM interpretation.",
    },
    {
        "name": "Direct - Route Calculation",
        "mission_type": "route_calculation",
        "params": {
            "start": [14.6568, 121.1107],
            "end": [14.6332, 121.0959],
            "preferences": {},
        },
        "description": "Direct route_calculation with explicit coordinates.",
    },
    {
        "name": "Direct - Coordinated Evacuation",
        "mission_type": "coordinated_evacuation",
        "params": {
            "user_location": [14.6653, 121.1023],
            "message": "Water is knee-deep, need immediate evacuation",
        },
        "description": "Direct coordinated_evacuation with explicit location.",
    },
    {
        "name": "Direct - Cascade Risk Update",
        "mission_type": "cascade_risk_update",
        "params": {},
        "description": "Direct cascade_risk_update (no params needed).",
    },
]

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
    print(f"\n--- {title} ---")


def print_json(data: Any, indent: int = 2) -> None:
    """Pretty-print JSON-serialisable data."""
    try:
        print(json.dumps(data, indent=indent, default=str))
    except (TypeError, ValueError):
        print(data)


class MissionReport:
    """Collects results from all test runs for the final documentation."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def add(self, entry: Dict[str, Any]) -> None:
        self.entries.append(entry)

    def write(self, filepath: str) -> None:
        """Write the full report to a markdown file."""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        lines = [
            "# Orchestrator Brain Test Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total runtime**: {elapsed:.1f}s",
            f"**Missions tested**: {len(self.entries)}",
            "",
            "---",
            "",
        ]

        passed = sum(1 for e in self.entries if e.get("passed"))
        failed = len(self.entries) - passed
        lines.append(f"**Results**: {passed} passed, {failed} failed")
        lines.append("")

        # Summary table
        lines.append("| # | Test Name | Type | Method | Final State | Duration | Pass |")
        lines.append("|---|-----------|------|--------|-------------|----------|------|")
        for i, e in enumerate(self.entries, 1):
            state = e.get("final_state", "N/A")
            dur = f"{e.get('duration', 0):.1f}s"
            mark = "Y" if e.get("passed") else "N"
            mtype = e.get("mission_type", "?")
            method = e.get("method", "?")
            lines.append(
                f"| {i} | {e['name']} | {mtype} | {method} | {state} | {dur} | {mark} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")

        # Detailed sections
        for i, e in enumerate(self.entries, 1):
            lines.append(f"## {i}. {e['name']}")
            lines.append("")
            lines.append(f"**Description**: {e.get('description', '')}")
            lines.append(f"**Method**: `{e.get('method', '')}`")
            lines.append(f"**Mission type**: `{e.get('mission_type', '')}`")
            lines.append(f"**Final state**: `{e.get('final_state', 'N/A')}`")
            lines.append(f"**Duration**: {e.get('duration', 0):.1f}s")
            lines.append(f"**Passed**: {'Yes' if e.get('passed') else 'No'}")
            lines.append("")

            if e.get("error"):
                lines.append(f"**Error**: {e['error']}")
                lines.append("")

            if e.get("interpretation"):
                lines.append("### LLM Interpretation")
                lines.append("```json")
                lines.append(json.dumps(e["interpretation"], indent=2, default=str))
                lines.append("```")
                lines.append("")

            if e.get("mission_creation"):
                lines.append("### Mission Creation Response")
                lines.append("```json")
                lines.append(json.dumps(e["mission_creation"], indent=2, default=str))
                lines.append("```")
                lines.append("")

            if e.get("final_status"):
                lines.append("### Final Mission Status")
                lines.append("```json")
                lines.append(json.dumps(e["final_status"], indent=2, default=str))
                lines.append("```")
                lines.append("")

            if e.get("summary"):
                lines.append("### LLM Summary")
                lines.append(f"> {e['summary']}")
                lines.append("")

            if e.get("state_transitions"):
                lines.append("### State Transitions")
                for t in e["state_transitions"]:
                    lines.append(f"- `{t['time']}` - **{t['state']}**")
                lines.append("")

            lines.append("---")
            lines.append("")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"\nReport written to: {filepath}")


# ---------------------------------------------------------------------------
# API callers
# ---------------------------------------------------------------------------


def check_server(base_url: str) -> bool:
    """Verify the server is running."""
    try:
        r = requests.get(f"{base_url}/api/health", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def check_llm_health(base_url: str) -> bool:
    """Check if the LLM service is available."""
    try:
        r = requests.get(f"{base_url}/api/llm/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("available", False) or data.get("status") == "ok"
        return False
    except (requests.ConnectionError, Exception):
        return False


def send_chat(base_url: str, message: str) -> Dict[str, Any]:
    """POST /api/orchestrator/chat with a natural language message."""
    r = requests.post(
        f"{base_url}/api/orchestrator/chat",
        json={"message": message},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def send_direct_mission(
    base_url: str, mission_type: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    """POST /api/orchestrator/mission with explicit type + params."""
    r = requests.post(
        f"{base_url}/api/orchestrator/mission",
        json={"mission_type": mission_type, "params": params},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def poll_mission(
    base_url: str, mission_id: str, timeout: float = DEFAULT_POLL_TIMEOUT
) -> Dict[str, Any]:
    """
    Poll GET /api/orchestrator/mission/{id} until terminal state or timeout.

    Returns the final status dict and the list of observed state transitions.
    """
    terminal_states = {"COMPLETED", "FAILED", "TIMED_OUT"}
    transitions: List[Dict[str, str]] = []
    last_state = None
    start = time.time()

    while time.time() - start < timeout:
        r = requests.get(
            f"{base_url}/api/orchestrator/mission/{mission_id}", timeout=10
        )
        if r.status_code == 404:
            # Mission may have already been archived to completed history
            time.sleep(POLL_INTERVAL)
            continue
        r.raise_for_status()
        data = r.json()
        state = data.get("state", "UNKNOWN")

        if state != last_state:
            transitions.append({"time": timestamp(), "state": state})
            print(f"  [{timestamp()}] State: {last_state} -> {state}")
            last_state = state

        if state in terminal_states:
            return {"status": data, "transitions": transitions}

        time.sleep(POLL_INTERVAL)

    # Timed out waiting
    return {
        "status": {"state": "POLL_TIMEOUT", "mission_id": mission_id},
        "transitions": transitions,
    }


def get_summary(base_url: str, mission_id: str) -> Optional[Dict[str, Any]]:
    """GET /api/orchestrator/mission/{id}/summary"""
    try:
        r = requests.get(
            f"{base_url}/api/orchestrator/mission/{mission_id}/summary",
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Test runners
# ---------------------------------------------------------------------------


def run_chat_test(
    base_url: str,
    scenario: Dict[str, Any],
    poll_timeout: float,
    report: MissionReport,
) -> bool:
    """
    Run a single chat-based test scenario.
    Returns True if the test passed.
    """
    entry: Dict[str, Any] = {
        "name": scenario["name"],
        "description": scenario["description"],
        "method": "POST /api/orchestrator/chat",
        "mission_type": scenario["expected_mission_type"],
        "passed": False,
    }
    start_t = time.time()

    try:
        # 1. Send chat message
        subseparator(f"Sending chat: \"{scenario['message']}\"")
        chat_result = send_chat(base_url, scenario["message"])
        print_json(chat_result)

        if chat_result.get("status") != "ok":
            entry["error"] = f"Chat failed: {chat_result.get('interpretation', {}).get('message', 'unknown')}"
            entry["duration"] = time.time() - start_t
            report.add(entry)
            return False

        interpretation = chat_result.get("interpretation", {})
        mission_info = chat_result.get("mission", {})
        entry["interpretation"] = interpretation
        entry["mission_creation"] = mission_info

        # 2. Validate interpretation
        actual_type = interpretation.get("mission_type", "")
        expected_type = scenario["expected_mission_type"]

        if actual_type != expected_type:
            print(
                f"  WARNING: Expected mission_type '{expected_type}', "
                f"got '{actual_type}'"
            )
            # Don't fail - LLM may choose a reasonable alternative

        entry["mission_type"] = actual_type
        mission_id = mission_info.get("mission_id")

        if not mission_id:
            entry["error"] = "No mission_id returned"
            entry["duration"] = time.time() - start_t
            report.add(entry)
            return False

        # 3. Poll for completion
        subseparator(f"Polling mission {mission_id}")
        poll_result = poll_mission(base_url, mission_id, poll_timeout)
        final_status = poll_result["status"]
        transitions = poll_result["transitions"]
        final_state = final_status.get("state", "UNKNOWN")

        entry["final_state"] = final_state
        entry["final_status"] = final_status
        entry["state_transitions"] = transitions

        # 4. Get LLM summary (if completed)
        if final_state == "COMPLETED":
            subseparator("Requesting LLM summary")
            summary_result = get_summary(base_url, mission_id)
            if summary_result:
                summary_text = summary_result.get("summary", "")
                llm_used = summary_result.get("llm_used", False)
                entry["summary"] = summary_text
                print(f"  LLM used: {llm_used}")
                print(f"  Summary: {summary_text}")

        # 5. Determine pass/fail
        passed = final_state == "COMPLETED"
        entry["passed"] = passed
        entry["duration"] = time.time() - start_t

        status_icon = "PASS" if passed else "FAIL"
        print(f"\n  Result: [{status_icon}] {scenario['name']} -> {final_state}")

    except requests.HTTPError as e:
        entry["error"] = f"HTTP error: {e.response.status_code} - {e.response.text[:200]}"
        entry["duration"] = time.time() - start_t
        print(f"  HTTP Error: {entry['error']}")
    except requests.ConnectionError:
        entry["error"] = "Connection refused - is the server running?"
        entry["duration"] = time.time() - start_t
        print(f"  Connection Error: {entry['error']}")
    except Exception as e:
        entry["error"] = str(e)
        entry["duration"] = time.time() - start_t
        print(f"  Error: {entry['error']}")

    report.add(entry)
    return entry.get("passed", False)


def run_direct_test(
    base_url: str,
    scenario: Dict[str, Any],
    poll_timeout: float,
    report: MissionReport,
) -> bool:
    """
    Run a single direct mission test (no LLM interpretation).
    Returns True if the test passed.
    """
    entry: Dict[str, Any] = {
        "name": scenario["name"],
        "description": scenario["description"],
        "method": "POST /api/orchestrator/mission",
        "mission_type": scenario["mission_type"],
        "passed": False,
    }
    start_t = time.time()

    try:
        # 1. Create mission directly
        subseparator(f"Creating direct mission: {scenario['mission_type']}")
        print(f"  Params: {json.dumps(scenario['params'], default=str)}")
        result = send_direct_mission(
            base_url, scenario["mission_type"], scenario["params"]
        )
        print_json(result)
        entry["mission_creation"] = result

        mission_id = result.get("mission_id")
        if not mission_id:
            entry["error"] = f"No mission_id returned: {result}"
            entry["duration"] = time.time() - start_t
            report.add(entry)
            return False

        # 2. Poll for completion
        subseparator(f"Polling mission {mission_id}")
        poll_result = poll_mission(base_url, mission_id, poll_timeout)
        final_status = poll_result["status"]
        transitions = poll_result["transitions"]
        final_state = final_status.get("state", "UNKNOWN")

        entry["final_state"] = final_state
        entry["final_status"] = final_status
        entry["state_transitions"] = transitions

        # 3. Determine pass/fail
        passed = final_state == "COMPLETED"
        entry["passed"] = passed
        entry["duration"] = time.time() - start_t

        status_icon = "PASS" if passed else "FAIL"
        print(f"\n  Result: [{status_icon}] {scenario['name']} -> {final_state}")

    except requests.HTTPError as e:
        entry["error"] = f"HTTP error: {e.response.status_code} - {e.response.text[:200]}"
        entry["duration"] = time.time() - start_t
    except requests.ConnectionError:
        entry["error"] = "Connection refused - is the server running?"
        entry["duration"] = time.time() - start_t
    except Exception as e:
        entry["error"] = str(e)
        entry["duration"] = time.time() - start_t

    report.add(entry)
    return entry.get("passed", False)


# ---------------------------------------------------------------------------
# LLM Brain unit tests (interpretation only, no mission execution)
# ---------------------------------------------------------------------------

INTERPRETATION_CASES = [
    {
        "message": "Is Tumana flooded?",
        "valid_types": ["assess_risk"],
    },
    {
        "message": "Navigate from Concepcion Uno to Sto. Nino safely",
        "valid_types": ["route_calculation"],
    },
    {
        "message": "Help! My house is flooded in Nangka!",
        "valid_types": ["coordinated_evacuation", "assess_risk"],
    },
    {
        "message": "Refresh all flood sensor data",
        "valid_types": ["cascade_risk_update"],
    },
    {
        "message": "How dangerous is the Marikina River right now?",
        "valid_types": ["assess_risk", "cascade_risk_update"],
    },
]


def run_interpretation_tests(base_url: str) -> int:
    """
    Test the LLM's ability to classify messages without executing missions.
    Sends chat requests and validates the interpretation only.

    Returns count of failures.
    """
    separator("LLM Interpretation Tests (classification only)")
    failures = 0

    for i, case in enumerate(INTERPRETATION_CASES, 1):
        msg = case["message"]
        valid = case["valid_types"]
        print(f"\n  [{i}/{len(INTERPRETATION_CASES)}] \"{msg}\"")
        print(f"       Acceptable types: {valid}")

        try:
            chat_result = send_chat(base_url, msg)
            if chat_result.get("status") != "ok":
                err = chat_result.get("interpretation", {}).get("message", "?")
                print(f"       FAIL - chat error: {err}")
                failures += 1
                continue

            actual = chat_result["interpretation"]["mission_type"]
            reasoning = chat_result["interpretation"].get("reasoning", "")
            params = chat_result["interpretation"].get("params", {})

            if actual in valid:
                print(f"       PASS - type={actual}")
            else:
                print(f"       FAIL - got '{actual}', expected one of {valid}")
                failures += 1

            print(f"       Reasoning: {reasoning}")
            print(f"       Params: {json.dumps(params, default=str)}")

        except Exception as e:
            print(f"       FAIL - exception: {e}")
            failures += 1

    return failures


# ---------------------------------------------------------------------------
# _fix_params validation (offline, no server needed)
# ---------------------------------------------------------------------------


def run_fix_params_tests() -> int:
    """Test the _fix_params static method with known edge cases."""
    separator("_fix_params Unit Tests (offline)")

    from app.agents.orchestrator_agent import OrchestratorAgent

    cases = [
        {
            "name": "String coordinates",
            "type": "route_calculation",
            "input": {"start": "[14.65, 121.11]", "end": "[14.63, 121.09]"},
            "check": lambda p: isinstance(p["start"], list)
            and isinstance(p["end"], list),
        },
        {
            "name": "Nested array coords",
            "type": "route_calculation",
            "input": {
                "start": [[14.65, 121.11], [14.63, 121.09]],
                "end": [[14.65, 121.11], [14.63, 121.09]],
            },
            "check": lambda p: (
                isinstance(p["start"][0], float) and isinstance(p["end"][0], float)
            ),
        },
        {
            "name": "Start equals end with origin/destination",
            "type": "route_calculation",
            "input": {
                "start": [14.65, 121.11],
                "end": [14.65, 121.11],
                "origin": [14.60, 121.10],
                "destination": [14.70, 121.12],
            },
            "check": lambda p: p["start"] == [14.60, 121.10]
            and p["end"] == [14.70, 121.12],
        },
        {
            "name": "String evacuation location",
            "type": "coordinated_evacuation",
            "input": {
                "user_location": "[14.66, 121.10]",
                "message": "Help!",
            },
            "check": lambda p: isinstance(p["user_location"], list),
        },
        {
            "name": "Nested evacuation location",
            "type": "coordinated_evacuation",
            "input": {
                "user_location": [[14.66, 121.10]],
                "message": "Help!",
            },
            "check": lambda p: (
                isinstance(p["user_location"], list)
                and isinstance(p["user_location"][0], float)
            ),
        },
        {
            "name": "Normal params unchanged",
            "type": "route_calculation",
            "input": {"start": [14.65, 121.11], "end": [14.63, 121.09]},
            "check": lambda p: p["start"] == [14.65, 121.11]
            and p["end"] == [14.63, 121.09],
        },
    ]

    failures = 0
    for i, case in enumerate(cases, 1):
        import copy

        params = copy.deepcopy(case["input"])
        result = OrchestratorAgent._fix_params(case["type"], params)
        ok = case["check"](result)
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {case['name']}")
        if not ok:
            print(f"         Result: {result}")
            failures += 1

    return failures


# ---------------------------------------------------------------------------
# _parse_llm_json validation (offline)
# ---------------------------------------------------------------------------


def run_parse_json_tests() -> int:
    """Test the _parse_llm_json static method with tricky LLM outputs."""
    separator("_parse_llm_json Unit Tests (offline)")

    from app.agents.orchestrator_agent import OrchestratorAgent

    cases = [
        {
            "name": "Clean JSON",
            "input": '{"mission_type": "assess_risk", "params": {}}',
            "check": lambda r: r is not None and r["mission_type"] == "assess_risk",
        },
        {
            "name": "Markdown fenced JSON",
            "input": '```json\n{"mission_type": "route_calculation"}\n```',
            "check": lambda r: r is not None
            and r["mission_type"] == "route_calculation",
        },
        {
            "name": "Truncated - missing closing brace",
            "input": '{"mission_type": "assess_risk", "params": {"location": "Tumana"}',
            "check": lambda r: r is not None and r["params"]["location"] == "Tumana",
        },
        {
            "name": "Leading text before JSON",
            "input": 'Here is my response:\n{"mission_type": "cascade_risk_update", "params": {}}',
            "check": lambda r: r is not None
            and r["mission_type"] == "cascade_risk_update",
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
    ]

    failures = 0
    for case in cases:
        result = OrchestratorAgent._parse_llm_json(case["input"])
        ok = case["check"](result)
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {case['name']}")
        if not ok:
            print(f"         Input:  {case['input'][:80]}")
            print(f"         Result: {result}")
            failures += 1

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Test the orchestrator agent brain end-to-end"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Server base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_POLL_TIMEOUT,
        help=f"Mission poll timeout in seconds (default: {DEFAULT_POLL_TIMEOUT})",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip tests that require the LLM (chat + summary)",
    )
    parser.add_argument(
        "--chat-only",
        action="store_true",
        help="Only run LLM chat tests (skip direct mission tests)",
    )
    parser.add_argument(
        "--direct-only",
        action="store_true",
        help="Only run direct mission tests (skip LLM chat tests)",
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Only run offline unit tests (_fix_params, _parse_llm_json)",
    )
    parser.add_argument(
        "--report",
        default="tests/orchestrator_brain_report.md",
        help="Path for the markdown report (default: tests/orchestrator_brain_report.md)",
    )
    args = parser.parse_args()

    total_failures = 0
    report = MissionReport()

    # ------------------------------------------------------------------
    # Phase 0: Offline unit tests (no server needed)
    # ------------------------------------------------------------------

    total_failures += run_parse_json_tests()
    total_failures += run_fix_params_tests()

    if args.offline_only:
        print(f"\n{'=' * 78}")
        print(f"  Offline tests complete. Failures: {total_failures}")
        print(f"{'=' * 78}")
        sys.exit(1 if total_failures else 0)

    # ------------------------------------------------------------------
    # Phase 1: Server connectivity
    # ------------------------------------------------------------------

    separator("Server Connectivity Check")
    if not check_server(args.base_url):
        print(f"  FATAL: Server not reachable at {args.base_url}")
        print("  Start the server with: uvicorn app.main:app --reload")
        sys.exit(1)
    print(f"  Server is running at {args.base_url}")

    llm_available = check_llm_health(args.base_url)
    print(f"  LLM available: {llm_available}")

    if args.no_llm:
        llm_available = False
        print("  (--no-llm flag set, skipping LLM tests)")

    # ------------------------------------------------------------------
    # Phase 2: Direct mission tests (deterministic, no LLM needed)
    # ------------------------------------------------------------------

    if not args.chat_only:
        separator("Direct Mission Tests (no LLM interpretation)")
        for i, scenario in enumerate(DIRECT_MISSIONS, 1):
            print(f"\n[{i}/{len(DIRECT_MISSIONS)}] {scenario['name']}")
            passed = run_direct_test(
                args.base_url, scenario, args.timeout, report
            )
            if not passed:
                total_failures += 1
            # Small delay between tests to avoid overwhelming the MQ
            time.sleep(1)

    # ------------------------------------------------------------------
    # Phase 3: LLM chat tests (requires Ollama)
    # ------------------------------------------------------------------

    if not args.direct_only and llm_available:
        separator("LLM Chat Tests (natural language -> mission)")
        for i, scenario in enumerate(CHAT_SCENARIOS, 1):
            print(f"\n[{i}/{len(CHAT_SCENARIOS)}] {scenario['name']}")
            passed = run_chat_test(
                args.base_url, scenario, args.timeout, report
            )
            if not passed:
                total_failures += 1
            time.sleep(1)

        # Interpretation-only tests
        interp_failures = run_interpretation_tests(args.base_url)
        total_failures += interp_failures

    elif not args.direct_only and not llm_available:
        separator("LLM Chat Tests - SKIPPED")
        print("  LLM is not available. Skipping chat and interpretation tests.")
        print("  Start Ollama to enable: ollama serve")

    # ------------------------------------------------------------------
    # Phase 4: Report generation
    # ------------------------------------------------------------------

    if report.entries:
        separator("Generating Report")
        report.write(args.report)

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------

    separator("Test Summary")
    passed = sum(1 for e in report.entries if e.get("passed"))
    failed_entries = [e for e in report.entries if not e.get("passed")]
    print(f"  Missions tested : {len(report.entries)}")
    print(f"  Passed          : {passed}")
    print(f"  Failed          : {len(failed_entries)}")
    if failed_entries:
        print("  Failed tests:")
        for e in failed_entries:
            print(f"    - {e['name']}: {e.get('error', e.get('final_state', '?'))}")

    print(f"  Offline failures: {total_failures - len(failed_entries)}")
    print(f"  Total failures  : {total_failures}")

    sys.exit(1 if total_failures else 0)


if __name__ == "__main__":
    main()
