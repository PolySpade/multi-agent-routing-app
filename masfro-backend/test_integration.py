#!/usr/bin/env python3
# filename: test_integration.py

"""
Integration Test Script for MAS-FRO Backend

This script performs integration tests to verify that all components
of the MAS-FRO system work together correctly.

Usage:
    python test_integration.py
"""

import sys
import time
from typing import Dict, Any


def print_header(title: str):
    """Print a formatted test section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status:8} | {test_name}")
    if details:
        print(f"         | {details}")


def test_imports():
    """Test that all modules can be imported."""
    print_header("Testing Module Imports")

    tests = []

    # Test agent imports
    try:
        from app.agents.flood_agent import FloodAgent
        tests.append(("FloodAgent", True, ""))
    except Exception as e:
        tests.append(("FloodAgent", False, str(e)))

    try:
        from app.agents.hazard_agent import HazardAgent
        tests.append(("HazardAgent", True, ""))
    except Exception as e:
        tests.append(("HazardAgent", False, str(e)))

    try:
        from app.agents.evacuation_manager_agent import EvacuationManagerAgent
        tests.append(("EvacuationManagerAgent", True, ""))
    except Exception as e:
        tests.append(("EvacuationManagerAgent", False, str(e)))

    # Test algorithm imports
    try:
        from app.algorithms.risk_aware_astar import risk_aware_astar
        tests.append(("risk_aware_astar", True, ""))
    except Exception as e:
        tests.append(("risk_aware_astar", False, str(e)))

    try:
        from app.algorithms.path_optimizer import find_k_shortest_paths
        tests.append(("path_optimizer", True, ""))
    except Exception as e:
        tests.append(("path_optimizer", False, str(e)))

    # Test communication imports
    try:
        from app.communication.acl_protocol import ACLMessage
        tests.append(("ACLMessage", True, ""))
    except Exception as e:
        tests.append(("ACLMessage", False, str(e)))

    try:
        from app.communication.message_queue import MessageQueue
        tests.append(("MessageQueue", True, ""))
    except Exception as e:
        tests.append(("MessageQueue", False, str(e)))

    # Test environment imports
    try:
        from app.environment.graph_manager import DynamicGraphEnvironment
        tests.append(("DynamicGraphEnvironment", True, ""))
    except Exception as e:
        tests.append(("DynamicGraphEnvironment", False, str(e)))

    try:
        from app.environment.risk_calculator import RiskCalculator
        tests.append(("RiskCalculator", True, ""))
    except Exception as e:
        tests.append(("RiskCalculator", False, str(e)))

    # Test ML model imports
    try:
        from app.ml_models.flood_predictor import FloodPredictor
        tests.append(("FloodPredictor", True, ""))
    except Exception as e:
        tests.append(("FloodPredictor", False, str(e)))

    try:
        from app.ml_models.nlp_processor import NLPProcessor
        tests.append(("NLPProcessor", True, ""))
    except Exception as e:
        tests.append(("NLPProcessor", False, str(e)))

    # Print results
    for test_name, passed, details in tests:
        print_test(test_name, passed, details)

    return all(passed for _, passed, _ in tests)


def test_agent_initialization():
    """Test that agents can be initialized."""
    print_header("Testing Agent Initialization")

    tests = []

    try:
        from app.environment.graph_manager import DynamicGraphEnvironment
        from app.agents.flood_agent import FloodAgent
        from app.agents.hazard_agent import HazardAgent
        from app.agents.evacuation_manager_agent import EvacuationManagerAgent

        env = DynamicGraphEnvironment()
        tests.append(("DynamicGraphEnvironment init", True, ""))

        flood_agent = FloodAgent("flood_001", env)
        tests.append(("FloodAgent init", True, f"ID: {flood_agent.agent_id}"))

        hazard_agent = HazardAgent("hazard_001", env)
        tests.append(("HazardAgent init", True, f"ID: {hazard_agent.agent_id}"))

        evac_manager = EvacuationManagerAgent("evac_001", env)
        tests.append(("EvacuationManagerAgent init", True, f"ID: {evac_manager.agent_id}"))

    except Exception as e:
        tests.append(("Agent initialization", False, str(e)))

    for test_name, passed, details in tests:
        print_test(test_name, passed, details)

    return all(passed for _, passed, _ in tests)


def test_risk_calculator():
    """Test risk calculator functionality."""
    print_header("Testing Risk Calculator")

    tests = []

    try:
        from app.environment.risk_calculator import RiskCalculator

        calc = RiskCalculator()
        tests.append(("RiskCalculator init", True, ""))

        # Test hydrological risk
        risk = calc.calculate_hydrological_risk(0.5, 1.0)
        tests.append((
            "Hydrological risk calculation",
            0.0 <= risk <= 1.0,
            f"Risk: {risk:.2f}"
        ))

        # Test composite risk
        comp_risk = calc.calculate_composite_risk(
            flood_depth=0.6,
            flow_velocity=1.2,
            road_type="residential"
        )
        tests.append((
            "Composite risk calculation",
            0.0 <= comp_risk <= 1.0,
            f"Risk: {comp_risk:.2f}"
        ))

        # Test passability
        passability = calc.calculate_passability_threshold(
            flood_depth=0.3,
            flow_velocity=0.5,
            vehicle_type="car"
        )
        tests.append((
            "Passability calculation",
            "passable" in passability,
            f"Passable: {passability['passable']}"
        ))

    except Exception as e:
        tests.append(("Risk Calculator", False, str(e)))

    for test_name, passed, details in tests:
        print_test(test_name, passed, details)

    return all(passed for _, passed, _ in tests)


def test_acl_protocol():
    """Test ACL protocol and message queue."""
    print_header("Testing ACL Protocol & Message Queue")

    tests = []

    try:
        from app.communication.acl_protocol import (
            ACLMessage,
            Performative,
            create_request_message
        )
        from app.communication.message_queue import MessageQueue

        # Test message creation
        msg = create_request_message(
            sender="agent1",
            receiver="agent2",
            action="test_action"
        )
        tests.append((
            "ACL message creation",
            msg.performative == Performative.REQUEST,
            f"Sender: {msg.sender}"
        ))

        # Test message queue
        mq = MessageQueue()
        mq.register_agent("agent1")
        mq.register_agent("agent2")

        success = mq.send_message(msg)
        tests.append(("Message queue send", success, ""))

        received = mq.receive_message("agent2", block=False)
        tests.append((
            "Message queue receive",
            received is not None if success else True,
            f"Received: {received.sender if received else 'None'}"
        ))

    except Exception as e:
        tests.append(("ACL Protocol", False, str(e)))

    for test_name, passed, details in tests:
        print_test(test_name, passed, details)

    return all(passed for _, passed, _ in tests)


def test_ml_models():
    """Test ML models."""
    print_header("Testing ML Models")

    tests = []

    try:
        from app.ml_models.flood_predictor import FloodPredictor
        from app.ml_models.nlp_processor import NLPProcessor

        # Test flood predictor
        predictor = FloodPredictor()
        tests.append(("FloodPredictor init", True, ""))

        risk = predictor.predict_flood_risk(
            rainfall_1h=30.0,
            river_level=1.5,
            elevation=15.0
        )
        tests.append((
            "Flood risk prediction",
            0.0 <= risk <= 1.0,
            f"Risk: {risk:.2f}"
        ))

        # Test NLP processor
        nlp = NLPProcessor()
        tests.append(("NLPProcessor init", True, ""))

        info = nlp.extract_flood_info("Baha sa Nangka! Tuhod level!")
        tests.append((
            "NLP flood info extraction",
            "severity" in info,
            f"Severity: {info.get('severity', 0):.2f}"
        ))

    except Exception as e:
        tests.append(("ML Models", False, str(e)))

    for test_name, passed, details in tests:
        print_test(test_name, passed, details)

    return all(passed for _, passed, _ in tests)


def test_api_app():
    """Test FastAPI application initialization."""
    print_header("Testing FastAPI Application")

    tests = []

    try:
        from app.main import app
        tests.append(("FastAPI app import", True, f"Title: {app.title}"))

        # Check that routes are registered
        route_paths = [route.path for route in app.routes]
        expected_routes = ["/", "/api/health", "/api/route", "/api/feedback"]

        for expected in expected_routes:
            found = any(expected in path for path in route_paths)
            tests.append((
                f"Route {expected}",
                found,
                "Registered" if found else "Missing"
            ))

    except Exception as e:
        tests.append(("FastAPI app", False, str(e)))

    for test_name, passed, details in tests:
        print_test(test_name, passed, details)

    return all(passed for _, passed, _ in tests)


def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("  MAS-FRO Backend Integration Tests")
    print("=" * 70)

    start_time = time.time()

    results = {
        "Module Imports": test_imports(),
        "Agent Initialization": test_agent_initialization(),
        "Risk Calculator": test_risk_calculator(),
        "ACL Protocol": test_acl_protocol(),
        "ML Models": test_ml_models(),
        "FastAPI Application": test_api_app(),
    }

    elapsed_time = time.time() - start_time

    # Print summary
    print_header("Test Summary")

    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)

    for test_suite, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status:8} | {test_suite}")

    print("\n" + "-" * 70)
    print(f"Total: {passed_tests}/{total_tests} test suites passed")
    print(f"Time: {elapsed_time:.2f} seconds")
    print("=" * 70)

    # Return exit code
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
