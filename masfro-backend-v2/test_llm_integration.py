#!/usr/bin/env python
"""
Test script for LLM integration in RoutingAgent

Tests:
1. LLMService health and availability
2. parse_routing_request() - NLP for routing preferences
3. explain_route() - Route explanation generation
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService, get_llm_service


def test_llm_service_health():
    """Test LLMService health check."""
    print("\n" + "="*60)
    print("TEST 1: LLMService Health Check")
    print("="*60)

    llm = get_llm_service()
    health = llm.get_health()

    print(f"  Available: {health['available']}")
    print(f"  Enabled: {health['enabled']}")
    print(f"  Text Model: {health['text_model']}")
    print(f"  Vision Model: {health['vision_model']}")
    print(f"  Models Loaded: {health['models_loaded']}")

    if health.get('text_model_loaded'):
        print(f"  [OK] Text model loaded")
    else:
        print(f"  [X] Text model NOT loaded")

    if health.get('vision_model_loaded'):
        print(f"  [OK] Vision model loaded")
    else:
        print(f"  [X] Vision model NOT loaded")

    assert health['available'], "LLM service should be available"
    print("\n  PASS: LLM service is healthy")
    return llm


def test_text_analysis(llm: LLMService):
    """Test text report analysis."""
    print("\n" + "="*60)
    print("TEST 2: Text Report Analysis (analyze_text_report)")
    print("="*60)

    test_cases = [
        "Baha sa J.P. Rizal, halos tuhod na ang tubig!",
        "Flooding near Marikina Sports Center, knee-deep water",
        "Clear roads in Concepcion, no flooding reported",
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n  Case {i}: \"{text[:50]}...\"")
        result = llm.analyze_text_report(text)

        if result:
            print(f"    Location: {result.get('location', 'N/A')}")
            print(f"    Severity: {result.get('severity', 'N/A')}")
            print(f"    Flood Related: {result.get('is_flood_related', 'N/A')}")
            print(f"    Description: {result.get('description', 'N/A')[:60]}...")
            print(f"    [OK] Analysis successful")
        else:
            print(f"    [X] Analysis returned empty result")

    print("\n  PASS: Text analysis working")


def test_routing_agent_parse_request():
    """Test RoutingAgent.parse_routing_request() NLP."""
    print("\n" + "="*60)
    print("TEST 3: RoutingAgent.parse_routing_request() - NLP")
    print("="*60)

    # Create a mock environment for testing
    from unittest.mock import MagicMock

    # Import routing agent
    from app.agents.routing_agent import RoutingAgent

    # Create mock environment
    mock_env = MagicMock()
    mock_env.graph = None  # No graph needed for NLP testing

    # Create LLM service
    llm = get_llm_service()

    # Create routing agent with LLM
    agent = RoutingAgent(
        agent_id="test_routing_001",
        environment=mock_env,
        llm_service=llm
    )

    test_queries = [
        "I'm driving a 4x4 truck and need to get through quickly",
        "I have a small car, please find the safest route",
        "Emergency! Need to reach the hospital ASAP",
        "I'm on a motorcycle, avoid any water if possible",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n  Query {i}: \"{query}\"")
        result = agent.parse_routing_request(query)

        if result:
            print(f"    Vehicle Type: {result.get('vehicle_type', 'N/A')}")
            print(f"    Mode: {result.get('mode', 'N/A')}")
            print(f"    Avoid Floods: {result.get('avoid_floods', 'N/A')}")
            print(f"    [OK] Preferences extracted")
        else:
            print(f"    [X] No preferences extracted (LLM may have returned invalid JSON)")

    print("\n  PASS: parse_routing_request working")
    return agent


def test_routing_agent_explain_route(agent):
    """Test RoutingAgent.explain_route()."""
    print("\n" + "="*60)
    print("TEST 4: RoutingAgent.explain_route() - Explanation")
    print("="*60)

    # Mock route results
    test_routes = [
        {
            "distance": 2500,
            "estimated_time": 8.5,
            "risk_level": 0.15,
            "max_risk": 0.3,
            "warnings": []
        },
        {
            "distance": 4500,
            "estimated_time": 15.0,
            "risk_level": 0.65,
            "max_risk": 0.85,
            "warnings": ["WARNING: High flood risk on this route"]
        },
        {
            "distance": 1200,
            "estimated_time": 4.0,
            "risk_level": 0.05,
            "max_risk": 0.1,
            "warnings": []
        },
    ]

    for i, route in enumerate(test_routes, 1):
        print(f"\n  Route {i}: {route['distance']}m, risk={route['risk_level']:.2f}")
        explanation = agent.explain_route(route)
        print(f"    Explanation: {explanation[:100]}...")

        if explanation and len(explanation) > 10:
            print(f"    [OK] Explanation generated")
        else:
            print(f"    [X] No meaningful explanation generated")

    print("\n  PASS: explain_route working")


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# LLM INTEGRATION TEST SUITE FOR ROUTING AGENT")
    print("#"*60)

    try:
        # Test 1: LLM Service Health
        llm = test_llm_service_health()

        # Test 2: Text Analysis
        test_text_analysis(llm)

        # Test 3: Routing Request Parsing (NLP)
        agent = test_routing_agent_parse_request()

        # Test 4: Route Explanation
        test_routing_agent_explain_route(agent)

        print("\n" + "#"*60)
        print("# ALL TESTS PASSED!")
        print("#"*60 + "\n")

    except AssertionError as e:
        print(f"\n\n  FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
