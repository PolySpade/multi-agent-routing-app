# filename: validation/verify_test_results.py

"""
Automated Test Results Verification Script

Checks if test results meet validation criteria and identifies issues.
Validates data completeness, success rates, risk scores, and performance.

Usage:
    python validation/verify_test_results.py <results_file.json>

Example:
    python validation/verify_test_results.py validation/results/comparison_results_20251120_172356.json

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple


def load_results(filepath: str) -> Dict:
    """Load results JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def verify_data_completeness(data: Dict) -> Tuple[bool, List[str]]:
    """Verify all expected data is present."""
    issues = []

    # Check metadata
    metadata = data.get('metadata', {})
    if metadata.get('total_metrics', 0) == 0:
        issues.append("No metrics found in results")

    expected_total = metadata.get('baseline_count', 0) + metadata.get('risk_aware_count', 0)
    actual_total = metadata.get('total_metrics', 0)

    if actual_total != expected_total:
        issues.append(
            f"Metric count mismatch: {actual_total} != {expected_total} "
            f"(baseline + risk_aware)"
        )

    # Check statistics exist
    stats = data.get('statistics', {})
    if not stats.get('baseline'):
        issues.append("Missing baseline statistics")
    if not stats.get('risk_aware'):
        issues.append("Missing risk-aware statistics")
    if not stats.get('comparison'):
        issues.append("Missing comparison statistics")

    return len(issues) == 0, issues


def verify_success_rates(data: Dict) -> Tuple[bool, List[str]]:
    """Verify success rates are acceptable."""
    issues = []

    stats = data.get('statistics', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})

    baseline_rate = baseline.get('success_rate', 0)
    risk_aware_rate = risk_aware.get('success_rate', 0)

    # Check baseline success rate
    if baseline_rate < 90:
        issues.append(
            f"Baseline success rate too low: {baseline_rate:.1f}% (expected >= 90%)"
        )
    elif baseline_rate < 95:
        issues.append(
            f"⚠️  Baseline success rate below target: {baseline_rate:.1f}% (target >= 95%)"
        )

    # Check risk-aware success rate
    if risk_aware_rate < 90:
        issues.append(
            f"Risk-aware success rate too low: {risk_aware_rate:.1f}% (expected >= 90%)"
        )
    elif risk_aware_rate < 95:
        issues.append(
            f"⚠️  Risk-aware success rate below target: {risk_aware_rate:.1f}% (target >= 95%)"
        )

    return len(issues) == 0, issues


def verify_risk_scores(data: Dict) -> Tuple[bool, List[str]]:
    """Verify risk scores are loaded and varying."""
    issues = []

    stats = data.get('statistics', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})
    comparison = stats.get('comparison', {})

    # Check if risk scores exist
    baseline_risk = baseline.get('avg_risk', 0)
    risk_aware_risk = risk_aware.get('avg_risk', 0)

    if baseline_risk == 0 and risk_aware_risk == 0:
        issues.append("[CRITICAL] All risk scores are 0 - GeoTIFF data not loaded!")
        issues.append("           Run: python validation/check_risk_scores.py")
        return False, issues

    # Check risk reduction
    risk_reduction = comparison.get('risk_reduction', 0)

    if risk_reduction == 0:
        issues.append("[WARNING] 0% risk reduction - risk scores may not be loaded properly")
    elif risk_reduction < 5:
        issues.append(
            f"[WARNING] Low risk reduction: {risk_reduction:.2f}% (expected >= 15%)"
        )
    elif risk_reduction < 15:
        issues.append(
            f"[WARNING] Risk reduction below target: {risk_reduction:.2f}% (target >= 15%)"
        )

    # Check for negative risk reduction (unexpected)
    if risk_reduction < 0:
        issues.append(
            f"[WARNING] Negative risk reduction: {risk_reduction:.2f}% (risk-aware is worse!)"
        )

    return len(issues) == 0, issues


def verify_performance_metrics(data: Dict) -> Tuple[bool, List[str]]:
    """Verify performance metrics are reasonable."""
    issues = []

    stats = data.get('statistics', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})
    comparison = stats.get('comparison', {})

    # Check distance overhead
    distance_overhead = comparison.get('distance_overhead', 0)

    if distance_overhead > 30:
        issues.append(
            f"[WARNING] High distance overhead: {distance_overhead:.2f}% (target <= 20%)"
        )
    elif distance_overhead < -5:
        issues.append(
            f"[WARNING] Negative distance overhead: {distance_overhead:.2f}% (unexpected)"
        )

    # Check computation time
    baseline_time = baseline.get('avg_computation_time', 0) * 1000  # to ms
    risk_aware_time = risk_aware.get('avg_computation_time', 0) * 1000

    if baseline_time > 200:
        issues.append(
            f"[WARNING] Slow baseline computation: {baseline_time:.2f}ms (target < 100ms)"
        )

    if risk_aware_time > 200:
        issues.append(
            f"[WARNING] Slow risk-aware computation: {risk_aware_time:.2f}ms (target < 100ms)"
        )

    return len(issues) == 0, issues


def verify_validation_criteria(data: Dict) -> Tuple[bool, List[str]]:
    """Check if results meet official validation criteria."""
    issues = []

    stats = data.get('statistics', {})
    comparison = stats.get('comparison', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})

    # Official validation criteria from README
    criteria = {
        "Risk reduction >= 15%": (
            comparison.get('risk_reduction', 0) >= 15,
            f"{comparison.get('risk_reduction', 0):.2f}%"
        ),
        "Distance overhead <= 20%": (
            comparison.get('distance_overhead', 0) <= 20,
            f"{comparison.get('distance_overhead', 0):.2f}%"
        ),
        "Baseline time < 100ms": (
            baseline.get('avg_computation_time', 0) < 0.1,
            f"{baseline.get('avg_computation_time', 0)*1000:.2f}ms"
        ),
        "Risk-aware time < 100ms": (
            risk_aware.get('avg_computation_time', 0) < 0.1,
            f"{risk_aware.get('avg_computation_time', 0)*1000:.2f}ms"
        ),
        "Baseline success >= 95%": (
            baseline.get('success_rate', 0) >= 95,
            f"{baseline.get('success_rate', 0):.1f}%"
        ),
        "Risk-aware success >= 95%": (
            risk_aware.get('success_rate', 0) >= 95,
            f"{risk_aware.get('success_rate', 0):.1f}%"
        ),
    }

    failed_criteria = []
    passed_criteria = []

    for criterion, (passed, value) in criteria.items():
        if passed:
            passed_criteria.append(f"  [PASS] {criterion} ({value})")
        else:
            failed_criteria.append(f"  [FAIL] {criterion} (actual: {value})")

    if failed_criteria:
        issues.append("Failed validation criteria:")
        issues.extend(failed_criteria)

    return len(failed_criteria) == 0, issues


def print_summary_statistics(data: Dict):
    """Print summary of key statistics."""
    stats = data.get('statistics', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})
    comparison = stats.get('comparison', {})

    print("\nKey Statistics:")
    print(f"\n  Success Rates:")
    print(f"    Baseline:    {baseline.get('success_rate', 0):.1f}%")
    print(f"    Risk-Aware:  {risk_aware.get('success_rate', 0):.1f}%")

    print(f"\n  Risk Scores:")
    print(f"    Baseline avg:    {baseline.get('avg_risk', 0):.4f}")
    print(f"    Risk-aware avg:  {risk_aware.get('avg_risk', 0):.4f}")
    print(f"    Reduction:       {comparison.get('risk_reduction', 0):.2f}%")

    print(f"\n  Distance:")
    print(f"    Baseline avg:    {baseline.get('avg_distance', 0):.1f}m")
    print(f"    Risk-aware avg:  {risk_aware.get('avg_distance', 0):.1f}m")
    print(f"    Overhead:        {comparison.get('distance_overhead', 0):.2f}%")

    print(f"\n  Computation Time:")
    print(f"    Baseline avg:    {baseline.get('avg_computation_time', 0)*1000:.2f}ms")
    print(f"    Risk-aware avg:  {risk_aware.get('avg_computation_time', 0)*1000:.2f}ms")
    print(f"    Overhead:        {comparison.get('time_overhead', 0):.2f}%")


def main():
    """Run all verification checks."""
    if len(sys.argv) < 2:
        print("Usage: python verify_test_results.py <results_file.json>")
        print("\nExample:")
        print("  python verify_test_results.py validation/results/comparison_results_20251120_172356.json")
        print("\nOr use wildcard to verify most recent:")
        print("  python verify_test_results.py validation/results/comparison_results_*.json")
        return 1

    results_file = sys.argv[1]

    # Handle wildcards (get most recent if multiple match)
    from glob import glob
    matching_files = glob(results_file)

    if not matching_files:
        print(f"❌ No results file found matching: {results_file}")
        return 1

    # Use most recent file if multiple match
    results_file = max(matching_files, key=lambda f: Path(f).stat().st_mtime)

    print(f"\n{'=' * 80}")
    print("TEST RESULTS VERIFICATION")
    print(f"{'=' * 80}\n")
    print(f"File: {results_file}\n")

    # Load data
    try:
        data = load_results(results_file)
    except Exception as e:
        print(f"❌ Failed to load results: {e}")
        return 1

    # Display basic info
    metadata = data.get('metadata', {})
    print(f"Total metrics: {metadata.get('total_metrics', 0):,}")
    print(f"  Baseline: {metadata.get('baseline_count', 0):,}")
    print(f"  Risk-aware: {metadata.get('risk_aware_count', 0):,}")
    print(f"Timestamp: {metadata.get('timestamp', 'unknown')}")

    # Run verification checks
    checks = [
        ("Data Completeness", verify_data_completeness),
        ("Success Rates", verify_success_rates),
        ("Risk Scores", verify_risk_scores),
        ("Performance Metrics", verify_performance_metrics),
        ("Validation Criteria", verify_validation_criteria),
    ]

    all_passed = True
    all_issues = []

    print(f"\n{'=' * 80}")
    print("VERIFICATION CHECKS")
    print(f"{'=' * 80}\n")

    for check_name, check_func in checks:
        print(f"[{check_name}]", end=" ")
        passed, issues = check_func(data)

        if passed:
            print("[PASS]")
        else:
            print("[FAIL]")
            all_passed = False
            all_issues.extend(issues)
            for issue in issues:
                print(f"    {issue}")

        print()

    # Display summary statistics
    print_summary_statistics(data)

    # Final verdict
    print(f"\n{'=' * 80}")
    print("FINAL VERDICT")
    print(f"{'=' * 80}\n")

    if all_passed:
        print("[OK] ALL CHECKS PASSED")
        print("\nYour 20,000 route test results are valid and meet all criteria!")
        print("\nNext steps:")
        print("  1. Generate analysis report:")
        print(f"     uv run python validation/statistical_analysis.py {results_file}")
        print("  2. Review detailed analysis in validation/analysis/analysis_report.txt")
        return 0
    else:
        print("[FAIL] SOME CHECKS FAILED")
        print(f"\nFound {len(all_issues)} issue(s):\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")

        print("\nPlease address these issues. See TEST_VALIDATION_GUIDE.md for help.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
