# filename: validation/pre_test_check.py

"""
Pre-Test Validation Script

Runs comprehensive checks before starting 20,000 route test.
Verifies graph, evacuation centers, risk scores, and system resources.

Usage:
    python validation/pre_test_check.py

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment
import networkx as nx


def check_graph():
    """Check graph is loaded and valid."""
    print("\n[1/5] Checking graph...")

    try:
        env = DynamicGraphEnvironment()
        graph = env.get_graph()

        if graph is None:
            print("  ❌ Graph not loaded")
            print("     Ensure marikina_graph.graphml exists in app/data/")
            return False

        num_nodes = len(graph.nodes())
        num_edges = len(graph.edges())

        print(f"  [OK] Graph loaded: {num_nodes:,} nodes, {num_edges:,} edges")

        # Check connectivity
        if nx.is_strongly_connected(graph):
            print("  [OK] Graph is strongly connected")
        else:
            components = list(nx.strongly_connected_components(graph))
            largest = max(components, key=len)
            coverage = len(largest) / num_nodes * 100

            print(f"  [WARNING] Graph has {len(components)} components")
            print(f"            Largest component: {len(largest):,} nodes ({coverage:.1f}%)")

            if coverage < 80:
                print("  [WARNING] Graph may have connectivity issues")

        return True

    except Exception as e:
        print(f"  [FAIL] Error loading graph: {e}")
        return False


def check_evacuation_centers():
    """Check evacuation centers CSV."""
    print("\n[2/5] Checking evacuation centers...")

    csv_path = Path(__file__).parent.parent / "app" / "data" / "evacuation_centers.csv"

    if not csv_path.exists():
        print(f"  [FAIL] Not found: {csv_path}")
        print("         Ensure evacuation_centers.csv exists in app/data/")
        return False

    try:
        # Count lines
        with open(csv_path) as f:
            lines = f.readlines()

        # Check for header
        if not lines:
            print("  [FAIL] CSV file is empty")
            return False

        num_centers = len(lines) - 1  # Subtract header
        print(f"  [OK] Found {num_centers} evacuation centers")

        if num_centers < 10:
            print(f"  [WARNING] Only {num_centers} centers (recommended >= 30)")
            print("            Low count may reduce route pair generation success rate")

        return True

    except Exception as e:
        print(f"  [FAIL] Error reading CSV: {e}")
        return False


def check_risk_scores():
    """Check if risk scores are loaded."""
    print("\n[3/5] Checking risk scores...")

    try:
        env = DynamicGraphEnvironment()
        graph = env.get_graph()

        edges_with_risk = sum(
            1 for u, v, data in graph.edges(data=True)
            if data.get('risk_score', 0) > 0
        )
        total_edges = len(graph.edges())
        coverage = edges_with_risk / total_edges * 100 if total_edges > 0 else 0

        print(f"  Edges with risk > 0: {edges_with_risk:,}/{total_edges:,} ({coverage:.1f}%)")

        if edges_with_risk == 0:
            print("  [FAIL] NO RISK SCORES FOUND!")
            print("\n  [WARNING] Validation will show 0% risk reduction without risk data!")
            print("\n  To load risk data:")
            print("    1. Ensure GeoTIFF files exist in app/data/geotiff/")
            print("    2. Use HazardAgent.load_geotiff() and update_risk_scores()")
            print("\n  Or run: python validation/check_risk_scores.py")
            return False

        if coverage < 10:
            print(f"  [WARNING] Low risk coverage ({coverage:.1f}%)")
            print("            Risk scores may not be fully loaded")
            return False

        print("  [OK] Risk scores are loaded")
        return True

    except Exception as e:
        print(f"  [FAIL] Error checking risk scores: {e}")
        return False


def check_disk_space():
    """Check available disk space."""
    print("\n[4/5] Checking disk space...")

    try:
        import shutil

        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)

        stat = shutil.disk_usage(results_dir)
        free_mb = stat.free / (1024 * 1024)

        print(f"  Free space: {free_mb:.0f} MB")

        if free_mb < 50:
            print("  [FAIL] Insufficient disk space (< 50 MB)")
            return False
        elif free_mb < 100:
            print("  [WARNING] Low disk space (< 100 MB)")
        else:
            print("  [OK] Sufficient disk space")

        return True

    except Exception as e:
        print(f"  [FAIL] Error checking disk space: {e}")
        return False


def check_dependencies():
    """Check required dependencies."""
    print("\n[5/5] Checking dependencies...")

    all_ok = True

    # Required dependencies
    required = {
        'networkx': 'NetworkX',
        'numpy': 'NumPy',
    }

    for module, name in required.items():
        try:
            __import__(module)
            print(f"  [OK] {name} installed")
        except ImportError:
            print(f"  [FAIL] {name} not installed")
            all_ok = False

    # Optional dependencies
    try:
        import matplotlib
        print("  [OK] Matplotlib installed (visualizations enabled)")
    except ImportError:
        print("  [INFO] Matplotlib not installed (visualizations will be skipped)")

    return all_ok


def estimate_test_time(num_pairs: int = 20000):
    """Estimate test execution time."""
    print(f"\n[Estimates for {num_pairs:,} pairs]")

    # Rough estimates based on typical performance
    pair_generation_time = num_pairs * 0.003  # ~3ms per pair
    route_computation_time = num_pairs * 0.25  # ~250ms per pair (both algorithms)

    total_seconds = pair_generation_time + route_computation_time
    total_minutes = total_seconds / 60

    print(f"  Pair generation: ~{pair_generation_time/60:.1f} minutes")
    print(f"  Route computation: ~{route_computation_time/60:.1f} minutes")
    print(f"  Total estimated time: ~{total_minutes:.0f} minutes ({total_minutes/60:.1f} hours)")
    print("\n  Note: Actual time varies based on CPU speed and graph complexity")


def main():
    """Run all pre-test checks."""
    print("=" * 60)
    print("PRE-TEST VALIDATION")
    print("=" * 60)

    checks = [
        ("Graph Loading", check_graph),
        ("Evacuation Centers", check_evacuation_centers),
        ("Risk Scores", check_risk_scores),
        ("Disk Space", check_disk_space),
        ("Dependencies", check_dependencies),
    ]

    results = []
    for name, check_func in checks:
        try:
            results.append(check_func())
        except Exception as e:
            print(f"\n  ❌ Unexpected error in {name}: {e}")
            results.append(False)

    # Time estimate
    estimate_test_time()

    # Summary
    print("\n" + "=" * 60)

    passed = sum(results)
    total = len(results)

    if all(results):
        print("[OK] ALL CHECKS PASSED")
        print(f"\n{passed}/{total} checks successful")
        print("\nYou are ready to run the 20,000 route test!")
        print("\nRecommended sequence:")
        print("  1. Quick test:  uv run python validation/algorithm_comparison.py --pairs 10")
        print("  2. Medium test: uv run python validation/algorithm_comparison.py --pairs 1000")
        print("  3. Full test:   uv run python validation/algorithm_comparison.py --pairs 20000")
        return 0
    else:
        print("[FAIL] SOME CHECKS FAILED")
        print(f"\n{passed}/{total} checks successful")
        print("\nPlease fix the issues above before running the full test.")
        print("See TEST_VALIDATION_GUIDE.md for detailed troubleshooting.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
