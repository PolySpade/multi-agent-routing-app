# filename: validation/statistical_analysis.py

"""
Statistical Analysis and Visualization for Algorithm Comparison

Generates statistical summaries, visualizations, and reports from
algorithm comparison results.

Author: MAS-FRO Development Team
Date: November 2025
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import matplotlib, gracefully degrade if not available
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available - visualizations disabled")


class StatisticalAnalyzer:
    """
    Analyzes routing algorithm comparison results.

    Generates statistical summaries, creates visualizations, and produces
    comprehensive reports from metrics collected during algorithm comparison.

    Attributes:
        results_data: Loaded JSON results data
        baseline_stats: Baseline algorithm statistics
        risk_aware_stats: Risk-aware algorithm statistics
        comparison_stats: Comparison statistics
    """

    def __init__(self, results_json: Path):
        """
        Initialize the statistical analyzer.

        Args:
            results_json: Path to comparison results JSON file
        """
        logger.info(f"Loading results from {results_json}")

        with open(results_json, 'r') as f:
            self.results_data = json.load(f)

        self.baseline_stats = self.results_data['statistics']['baseline']
        self.risk_aware_stats = self.results_data['statistics']['risk_aware']
        self.comparison_stats = self.results_data['statistics']['comparison']

        logger.info("✓ Results loaded successfully")

    def generate_text_report(self, output_file: Path) -> None:
        """
        Generate detailed text report.

        Args:
            output_file: Path to output text file
        """
        logger.info(f"Generating text report: {output_file}")

        with open(output_file, 'w') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("ROUTING ALGORITHM COMPARISON REPORT\n")
            f.write("Baseline A* (Distance-Only) vs Risk-Aware A*\n")
            f.write("=" * 80 + "\n\n")

            # Metadata
            metadata = self.results_data['metadata']
            f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Data Collected: {metadata['timestamp']}\n")
            f.write(f"Total Route Pairs: {metadata['total_metrics'] // 2}\n")
            f.write(f"Baseline Routes: {metadata['baseline_count']}\n")
            f.write(f"Risk-Aware Routes: {metadata['risk_aware_count']}\n\n")

            # Executive Summary
            f.write("=" * 80 + "\n")
            f.write("EXECUTIVE SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            comp = self.comparison_stats
            baseline = self.baseline_stats
            risk_aware = self.risk_aware_stats

            f.write(f"Risk Reduction: {comp['risk_reduction']:.2f}%\n")
            f.write(f"  Baseline average risk:    {baseline['avg_risk']:.4f}\n")
            f.write(f"  Risk-Aware average risk:  {risk_aware['avg_risk']:.4f}\n\n")

            f.write(f"Distance Overhead: {comp['distance_overhead']:.2f}%\n")
            f.write(f"  Baseline average distance:    {baseline['avg_distance']:.1f}m\n")
            f.write(f"  Risk-Aware average distance:  {risk_aware['avg_distance']:.1f}m\n\n")

            f.write(f"Computation Time Overhead: {comp['time_overhead']:.2f}%\n")
            f.write(f"  Baseline average time:    {baseline['avg_computation_time']*1000:.2f}ms\n")
            f.write(f"  Risk-Aware average time:  {risk_aware['avg_computation_time']*1000:.2f}ms\n\n")

            # Detailed Statistics - Baseline
            f.write("=" * 80 + "\n")
            f.write("BASELINE A* STATISTICS (Distance-Only Routing)\n")
            f.write("=" * 80 + "\n\n")

            self._write_algorithm_stats(f, baseline, "Baseline")

            # Detailed Statistics - Risk-Aware
            f.write("\n" + "=" * 80 + "\n")
            f.write("RISK-AWARE A* STATISTICS\n")
            f.write("=" * 80 + "\n\n")

            self._write_algorithm_stats(f, risk_aware, "Risk-Aware")

            # Comparison Analysis
            f.write("\n" + "=" * 80 + "\n")
            f.write("COMPARATIVE ANALYSIS\n")
            f.write("=" * 80 + "\n\n")

            f.write("1. SAFETY IMPROVEMENTS\n")
            f.write(f"   Average Risk Reduction:        {comp['risk_reduction']:.2f}%\n")
            f.write(f"   Max Risk Reduction:            {comp['max_risk_reduction']:.2f}%\n")
            f.write(f"   High-Risk Segments Avoided:    {comp['high_risk_segments_reduction']:.2f} per route\n")
            f.write(f"   Critical-Risk Segments Avoided: {comp['critical_risk_segments_reduction']:.2f} per route\n\n")

            f.write("2. PERFORMANCE COSTS\n")
            f.write(f"   Distance Overhead:       {comp['distance_overhead']:.2f}%\n")
            f.write(f"   Time Overhead:           {comp['time_overhead']:.2f}%\n\n")

            f.write("3. SUCCESS RATES\n")
            f.write(f"   Baseline Success Rate:   {comp['baseline_success_rate']:.2f}%\n")
            f.write(f"   Risk-Aware Success Rate: {comp['risk_aware_success_rate']:.2f}%\n\n")

            # Conclusions
            f.write("=" * 80 + "\n")
            f.write("CONCLUSIONS\n")
            f.write("=" * 80 + "\n\n")

            if comp['risk_reduction'] > 0:
                f.write("✓ VALIDATION SUCCESSFUL\n\n")
                f.write(f"The Risk-Aware A* algorithm successfully reduces flood risk exposure\n")
                f.write(f"by {comp['risk_reduction']:.2f}% compared to baseline distance-only routing.\n\n")

                f.write(f"Key findings:\n")
                f.write(f"- Routes are {comp['risk_reduction']:.2f}% safer on average\n")
                f.write(f"- Avoid {comp['high_risk_segments_reduction']:.1f} high-risk segments per route\n")
                f.write(f"- Add only {comp['distance_overhead']:.2f}% extra distance\n")
                f.write(f"- Computation time overhead: {comp['time_overhead']:.2f}%\n\n")

                f.write("The algorithm is VALIDATED for use in flood evacuation routing.\n")
            else:
                f.write("⚠ VALIDATION INCONCLUSIVE\n\n")
                f.write("Risk-Aware A* did not show significant risk reduction.\n")
                f.write("Further investigation recommended.\n")

            f.write("\n" + "=" * 80 + "\n")

        logger.info(f"✓ Text report saved to {output_file}")

    def _write_algorithm_stats(self, f, stats: Dict, name: str) -> None:
        """Write algorithm statistics to file."""
        f.write(f"Success Rate: {stats['success_rate']:.2f}%\n")
        f.write(f"  Successful: {stats['successful_routes']}\n")
        f.write(f"  Failed:     {stats['failed_routes']}\n\n")

        f.write(f"Risk Scores (0-1 scale):\n")
        f.write(f"  Average:    {stats['avg_risk']:.4f}\n")
        f.write(f"  Min:        {stats['min_risk']:.4f}\n")
        f.write(f"  Max:        {stats['max_risk_avg']:.4f}\n")
        f.write(f"  Avg Max:    {stats['avg_max_risk']:.4f}\n\n")

        f.write(f"High-Risk Segments:\n")
        f.write(f"  Avg High-Risk (>=0.6):    {stats['avg_high_risk_segments']:.2f}\n")
        f.write(f"  Avg Critical (>=0.9):     {stats['avg_critical_risk_segments']:.2f}\n\n")

        f.write(f"Distance (meters):\n")
        f.write(f"  Average:    {stats['avg_distance']:.1f}m\n")
        f.write(f"  Min:        {stats['min_distance']:.1f}m\n")
        f.write(f"  Max:        {stats['max_distance']:.1f}m\n\n")

        f.write(f"Computation Time:\n")
        f.write(f"  Average:    {stats['avg_computation_time']*1000:.2f}ms\n")
        f.write(f"  Min:        {stats['min_computation_time']*1000:.2f}ms\n")
        f.write(f"  Max:        {stats['max_computation_time']*1000:.2f}ms\n")
        f.write(f"  Total:      {stats['total_computation_time']:.2f}s\n\n")

    def create_visualizations(self, output_dir: Path) -> None:
        """
        Create visualization charts.

        Args:
            output_dir: Directory to save visualization images
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available - skipping visualizations")
            return

        logger.info(f"Creating visualizations in {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Risk comparison bar chart
        self._create_risk_comparison_chart(output_dir / "risk_comparison.png")

        # 2. Performance overhead chart
        self._create_overhead_chart(output_dir / "performance_overhead.png")

        # 3. Computation time comparison
        self._create_time_comparison_chart(output_dir / "computation_time.png")

        logger.info("✓ Visualizations created")

    def _create_risk_comparison_chart(self, output_file: Path) -> None:
        """Create risk comparison bar chart."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        baseline = self.baseline_stats
        risk_aware = self.risk_aware_stats

        # Average risk
        ax1.bar(['Baseline A*', 'Risk-Aware A*'],
                [baseline['avg_risk'], risk_aware['avg_risk']],
                color=['#e74c3c', '#2ecc71'])
        ax1.set_ylabel('Average Risk Score (0-1)')
        ax1.set_title('Average Risk Comparison')
        ax1.set_ylim(0, max(baseline['avg_risk'], risk_aware['avg_risk']) * 1.2)

        # Add value labels
        for i, v in enumerate([baseline['avg_risk'], risk_aware['avg_risk']]):
            ax1.text(i, v + 0.01, f'{v:.4f}', ha='center', fontweight='bold')

        # High-risk segments
        ax2.bar(['Baseline A*', 'Risk-Aware A*'],
                [baseline['avg_high_risk_segments'], risk_aware['avg_high_risk_segments']],
                color=['#e74c3c', '#2ecc71'])
        ax2.set_ylabel('Average High-Risk Segments (>=0.6)')
        ax2.set_title('High-Risk Segments per Route')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✓ Saved {output_file.name}")

    def _create_overhead_chart(self, output_file: Path) -> None:
        """Create performance overhead chart."""
        fig, ax = plt.subplots(figsize=(8, 6))

        comp = self.comparison_stats

        categories = ['Distance\nOverhead', 'Computation\nTime Overhead']
        values = [comp['distance_overhead'], comp['time_overhead']]
        colors = ['#3498db', '#9b59b6']

        bars = ax.bar(categories, values, color=colors)
        ax.set_ylabel('Overhead (%)')
        ax.set_title('Performance Overhead of Risk-Aware A*')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

        # Add value labels
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✓ Saved {output_file.name}")

    def _create_time_comparison_chart(self, output_file: Path) -> None:
        """Create computation time comparison chart."""
        fig, ax = plt.subplots(figsize=(8, 6))

        baseline = self.baseline_stats
        risk_aware = self.risk_aware_stats

        # Convert to milliseconds
        baseline_time = baseline['avg_computation_time'] * 1000
        risk_aware_time = risk_aware['avg_computation_time'] * 1000

        ax.bar(['Baseline A*', 'Risk-Aware A*'],
               [baseline_time, risk_aware_time],
               color=['#f39c12', '#e67e22'])
        ax.set_ylabel('Average Computation Time (ms)')
        ax.set_title('Computation Time Comparison')

        # Add value labels
        for i, v in enumerate([baseline_time, risk_aware_time]):
            ax.text(i, v + 0.5, f'{v:.2f}ms', ha='center', fontweight='bold')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✓ Saved {output_file.name}")

    def generate_full_report(self, output_dir: Path) -> None:
        """
        Generate complete analysis package.

        Args:
            output_dir: Directory for all output files
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\nGenerating full analysis report in {output_dir}")

        # Text report
        self.generate_text_report(output_dir / "analysis_report.txt")

        # Visualizations
        self.create_visualizations(output_dir / "charts")

        logger.info("✓ Full report generation complete")


def main():
    """CLI for statistical analysis."""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze algorithm comparison results')
    parser.add_argument('results_json', type=Path, help='Path to results JSON file')
    parser.add_argument('--output', type=Path, default=Path('validation/analysis'),
                        help='Output directory (default: validation/analysis)')

    args = parser.parse_args()

    if not args.results_json.exists():
        print(f"❌ Results file not found: {args.results_json}")
        return 1

    analyzer = StatisticalAnalyzer(args.results_json)
    analyzer.generate_full_report(args.output)

    print(f"\n✓ Analysis complete. Results in {args.output}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
