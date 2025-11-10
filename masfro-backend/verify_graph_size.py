#!/usr/bin/env python3
"""
Script to verify actual graph size (nodes and edges) for presentation verification.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.environment.graph_manager import DynamicGraphEnvironment
    import networkx as nx
    
    print("Loading graph...")
    env = DynamicGraphEnvironment()
    graph = env.get_graph()
    
    if graph is None:
        print("ERROR: Graph failed to load")
        sys.exit(1)
    
    num_nodes = len(graph.nodes())
    num_edges = len(graph.edges())
    
    print(f"\n=== Graph Size Verification ===")
    print(f"Actual nodes: {num_nodes:,}")
    print(f"Actual edges: {num_edges:,}")
    print(f"\nClaimed in slides: ~2,500 nodes, ~5,000 edges")
    print(f"\nDifference:")
    print(f"  Nodes: {num_nodes - 2500:+,} ({((num_nodes / 2500) - 1) * 100:+.1f}%)")
    print(f"  Edges: {num_edges - 5000:+,} ({((num_edges / 5000) - 1) * 100:+.1f}%)")
    
    # Check if graph is MultiDiGraph
    if isinstance(graph, nx.MultiDiGraph):
        print(f"\nGraph type: MultiDiGraph (as expected)")
    else:
        print(f"\nGraph type: {type(graph)} (expected MultiDiGraph)")
    
    # Additional statistics
    if num_nodes > 0:
        avg_degree = (2 * num_edges) / num_nodes if not graph.is_directed() else num_edges / num_nodes
        print(f"Average degree: {avg_degree:.2f}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

