#!/usr/bin/env python3
"""
Diagnostic script to understand why routes aren't changing around high-risk zones.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.routing_agent import RoutingAgent
import networkx as nx

def diagnose_routing():
    print("="*80)
    print("ROUTING DIAGNOSTIC")
    print("="*80)

    # Load environment
    print("\n[1] Loading environment...")
    env = DynamicGraphEnvironment()
    print(f"Graph: {env.graph.number_of_nodes()} nodes, {env.graph.number_of_edges()} edges")

    # Create routing agent
    routing_agent = RoutingAgent("diagnostic", env)

    # Test route
    start = (14.6507, 121.1029)
    end = (14.6303, 121.1084)

    print(f"\n[2] Calculating baseline route...")
    route1 = routing_agent.calculate_route(start, end)
    print(f"  Path nodes: {len(route1['path'])}")
    print(f"  Distance: {route1['distance']/1000:.2f} km")
    print(f"  Risk: {route1['risk_level']:.3f}")

    # Find midpoint
    mid_idx = len(route1['path']) // 2
    mid_coords = route1['path'][mid_idx]

    print(f"\n[3] Creating high-risk zone at path midpoint...")
    print(f"  Midpoint: {mid_coords}")

    # Set risk on edges near midpoint
    radius_deg = 0.25 / 111.0
    affected = 0

    for u, v, key, data in env.graph.edges(keys=True, data=True):
        u_data = env.graph.nodes[u]
        v_data = env.graph.nodes[v]

        mid_lat = (float(u_data['y']) + float(v_data['y'])) / 2
        mid_lon = (float(u_data['x']) + float(v_data['x'])) / 2

        import numpy as np
        dist = np.sqrt((mid_lat - mid_coords[0])**2 + (mid_lon - mid_coords[1])**2)

        if dist <= radius_deg:
            env.update_edge_risk(u, v, key, 0.95)
            affected += 1

    print(f"  Marked {affected} edges as high-risk (0.95)")

    # Sample check: verify risk scores were actually set
    print(f"\n[4] Verifying risk scores on edges...")
    high_risk_count = 0
    sample_edges = []

    for u, v, key, data in env.graph.edges(keys=True, data=True):
        risk = data.get('risk_score', 0.0)
        if risk >= 0.9:
            high_risk_count += 1
            if len(sample_edges) < 5:
                sample_edges.append((u, v, key, risk, data.get('length', 0)))

    print(f"  Total edges with risk >= 0.9: {high_risk_count}")
    print(f"  Sample high-risk edges:")
    for u, v, key, risk, length in sample_edges:
        print(f"    ({u}, {v}, {key}): risk={risk:.2f}, length={length:.1f}m")

    # Try routing again
    print(f"\n[5] Recalculating route with high-risk zone...")
    route2 = routing_agent.calculate_route(start, end)
    print(f"  Path nodes: {len(route2['path'])}")
    print(f"  Distance: {route2['distance']/1000:.2f} km")
    print(f"  Risk: {route2['risk_level']:.3f}")
    print(f"  Max Risk: {route2['max_risk']:.3f}")

    # Compare paths
    print(f"\n[6] Path comparison:")
    print(f"  Same path? {route1['path'] == route2['path']}")
    print(f"  Distance change: {(route2['distance'] - route1['distance']):.0f}m")
    print(f"  Risk change: {(route2['max_risk'] - route1['max_risk']):.3f}")

    # Check if path goes through high-risk zone
    print(f"\n[7] Checking if route passes through high-risk zone...")
    passes_through = False
    for coord in route2['path']:
        dist = np.sqrt((coord[0] - mid_coords[0])**2 + (coord[1] - mid_coords[1])**2)
        if dist <= radius_deg:
            passes_through = True
            print(f"  YES - Route passes through high-risk zone at {coord}")
            break

    if not passes_through:
        print(f"  NO - Route successfully avoids high-risk zone!")
    else:
        print(f"\n  [PROBLEM] Route still goes through high-risk area!")
        print(f"  This suggests the algorithm is not properly avoiding risky edges.")

if __name__ == "__main__":
    try:
        diagnose_routing()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
