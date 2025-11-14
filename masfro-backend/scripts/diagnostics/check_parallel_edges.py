#!/usr/bin/env python3
"""
Check if routes use parallel edges that bypass high-risk markings.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment
import networkx as nx

def check_parallel_edges():
    print("="*80)
    print("PARALLEL EDGE ANALYSIS")
    print("="*80)

    env = DynamicGraphEnvironment()

    # Count parallel edges
    print(f"\nTotal nodes: {env.graph.number_of_nodes()}")
    print(f"Total edges: {env.graph.number_of_edges()}")

    # Find examples of parallel edges
    parallel_count = 0
    examples = []

    checked_pairs = set()
    for u, v, key, data in env.graph.edges(keys=True, data=True):
        pair = (u, v)
        if pair in checked_pairs:
            continue
        checked_pairs.add(pair)

        # Count how many parallel edges exist for this (u,v) pair
        all_edges = list(env.graph[u][v].keys())
        if len(all_edges) > 1:
            parallel_count += 1
            if len(examples) < 10:
                examples.append((u, v, all_edges))

    print(f"\nNode pairs with parallel edges: {parallel_count}")
    print(f"\nExamples (first 10):")
    for u, v, keys in examples:
        print(f"  ({u}, {v}): {len(keys)} parallel edges (keys: {keys})")

        # Show risk scores for each parallel edge
        for key in keys:
            edge_data = env.graph[u][v][key]
            risk = edge_data.get('risk_score', 0.0)
            length = edge_data.get('length', 0.0)
            print(f"    Key {key}: risk={risk:.2f}, length={length:.1f}m")

    # Test: set high risk on ONE parallel edge, see if route uses the other
    print(f"\n\nTEST: Set risk on one parallel edge only...")
    if examples:
        u, v, keys = examples[0]
        print(f"Using edge pair ({u}, {v}) with {len(keys)} parallel edges")

        # Set high risk on key 0 only
        env.update_edge_risk(u, v, 0, 0.95)

        print(f"\nAfter setting risk on key 0:")
        for key in keys:
            edge_data = env.graph[u][v][key]
            risk = edge_data.get('risk_score', 0.0)
            print(f"  Key {key}: risk={risk:.2f}")

        if len(keys) > 1:
            print(f"\n[INSIGHT] NetworkX A* might use key {keys[1]} (risk={env.graph[u][v][keys[1]].get('risk_score', 0.0):.2f}) instead of key 0!")

if __name__ == "__main__":
    try:
        check_parallel_edges()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
