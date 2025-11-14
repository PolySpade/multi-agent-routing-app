#!/usr/bin/env python3
"""
Quick runner for FloodAgent service tests.

This script provides a simple way to test individual services or run comprehensive tests.

Usage:
    python run_flood_service_tests.py [service_name]
    
    service_name options:
    - river      : Test PAGASA river level scraping
    - weather    : Test OpenWeatherMap API
    - dam        : Test PAGASA dam level scraping  
    - agent      : Test FloodAgent integration
    - all        : Run all tests (default)

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from test_flood_agent_services import FloodAgentServiceTester

console = Console()


def main():
    """Main execution with command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test FloodAgent services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_flood_service_tests.py              # Run all tests
    python run_flood_service_tests.py river        # Test river scraper only
    python run_flood_service_tests.py weather      # Test weather service only
    python run_flood_service_tests.py dam          # Test dam scraper only
    python run_flood_service_tests.py agent        # Test FloodAgent integration
        """
    )
    
    parser.add_argument(
        'service',
        nargs='?',
        choices=['river', 'weather', 'dam', 'agent', 'all'],
        default='all',
        help='Service to test (default: all)'
    )
    
    parser.add_argument(
        '--output',
        '-o',
        help='Output file for results (JSON format)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = FloodAgentServiceTester()
    
    console.print(f"\n[bold green]Testing {args.service.upper()} Service(s)[/bold green]")
    console.print("=" * 50)
    
    # Run specific test based on argument
    if args.service == 'river':
        result = tester.test_river_scraper()
        console.print(f"\n[bold]Result:[/bold] {result}")
        
    elif args.service == 'weather':
        result = tester.test_weather_service()
        console.print(f"\n[bold]Result:[/bold] {result}")
        
    elif args.service == 'dam':
        result = tester.test_dam_scraper()
        console.print(f"\n[bold]Result:[/bold] {result}")
        
    elif args.service == 'agent':
        result = tester.test_flood_agent_integration()
        console.print(f"\n[bold]Result:[/bold] {result}")
        
    elif args.service == 'all':
        tester.run_all_tests()
        
    # Save output if requested
    if args.output:
        import json
        from datetime import datetime
        
        output_data = {
            "test_type": args.service,
            "timestamp": datetime.now().isoformat(),
            "results": tester.results
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
            
        console.print(f"\n📄 Results saved to: {args.output}")


if __name__ == "__main__":
    main()