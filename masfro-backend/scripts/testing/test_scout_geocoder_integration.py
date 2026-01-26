# filename: scripts/test_scout_geocoder_integration.py

"""
Integration Test: Scout Agent → NLP → Geocoder → HazardAgent → Graph Updates
=============================================================================

Tests the complete data flow from social media tweets through the entire
processing pipeline with coordinate-based spatial risk propagation.

Flow tested:
1. Scout Agent receives tweets
2. NLP Processor extracts flood information
3. LocationGeocoder adds coordinates
4. HazardAgent receives reports with coordinates
5. Graph risk is updated spatially with distance decay

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml_models.nlp_processor import NLPProcessor
from app.ml_models.location_geocoder import LocationGeocoder
from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_synthetic_tweets(scenario: str = "moderate") -> list:
    """
    Load synthetic tweet data for testing.

    Args:
        scenario: Which scenario to load (minor, moderate, severe)

    Returns:
        List of tweet dictionaries
    """
    data_dir = Path(__file__).parent.parent / "app" / "data"
    synthetic_file = data_dir / "scout_synthetic_data.json"

    if not synthetic_file.exists():
        logger.warning(f"Synthetic data file not found: {synthetic_file}")
        # Create sample tweets if file doesn't exist
        return create_sample_tweets()

    with open(synthetic_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Get tweets from specified scenario
    if scenario in data:
        return data[scenario]
    else:
        logger.warning(f"Scenario '{scenario}' not found, using all tweets")
        return data.get("moderate", [])


def create_sample_tweets() -> list:
    """
    Create sample tweets for testing if synthetic data file doesn't exist.

    Returns:
        List of sample tweet dictionaries
    """
    return [
        {
            "tweet_id": "test001",
            "username": "test_user1",
            "text": "Baha sa Nangka! Tuhod level!",
            "timestamp": datetime.now().isoformat(),
            "url": "https://x.com/test_user1/status/test001",
            "replies": "5",
            "retweets": "10",
            "likes": "25"
        },
        {
            "tweet_id": "test002",
            "username": "test_user2",
            "text": "Waist deep flood sa SM Marikina parking lot",
            "timestamp": datetime.now().isoformat(),
            "url": "https://x.com/test_user2/status/test002",
            "replies": "15",
            "retweets": "30",
            "likes": "80"
        },
        {
            "tweet_id": "test003",
            "username": "test_user3",
            "text": "Okay na sa Concepcion Uno, keri pa dumaan",
            "timestamp": datetime.now().isoformat(),
            "url": "https://x.com/test_user3/status/test003",
            "replies": "2",
            "retweets": "5",
            "likes": "12"
        },
        {
            "tweet_id": "test004",
            "username": "test_user4",
            "text": "Heavy traffic sa EDSA wala namang baha",
            "timestamp": datetime.now().isoformat(),
            "url": "https://x.com/test_user4/status/test004",
            "replies": "3",
            "retweets": "1",
            "likes": "5"
        }
    ]


def test_nlp_extraction():
    """Test NLP processor extraction."""
    logger.info("\n=== TEST 1: NLP Extraction ===")

    nlp = NLPProcessor()

    test_texts = [
        "Baha sa Nangka! Tuhod level!",
        "Waist deep flood sa SM Marikina",
        "Clear na sa Tumana Bridge",
        "Heavy rain pero walang baha"
    ]

    results = []
    for text in test_texts:
        result = nlp.extract_flood_info(text)
        results.append(result)
        logger.info(
            f"Text: {text}\n"
            f"  Location: {result.get('location')}\n"
            f"  Flood-related: {result.get('is_flood_related')}\n"
            f"  Severity: {result.get('severity'):.2f}\n"
            f"  Type: {result.get('report_type')}\n"
        )

    # Assertions
    assert results[0]['is_flood_related'], "Should detect flood in text 1"
    assert results[0]['location'] == "Nangka", "Should extract Nangka location"
    assert not results[3]['is_flood_related'], "Should not detect flood in text 4"

    logger.info("✅ NLP extraction test passed\n")
    return results


def test_geocoding():
    """Test LocationGeocoder coordinate extraction."""
    logger.info("\n=== TEST 2: Geocoding ===")

    geocoder = LocationGeocoder()

    test_locations = [
        "Nangka",
        "SM Marikina",
        "Tumana Bridge",
        "Unknown Location"
    ]

    for location in test_locations:
        coords = geocoder.get_coordinates(location)
        if coords:
            logger.info(f"{location}: ({coords[0]:.4f}, {coords[1]:.4f})")
        else:
            logger.info(f"{location}: NOT FOUND")

    # Assertions
    nangka_coords = geocoder.get_coordinates("Nangka")
    assert nangka_coords is not None, "Should find Nangka coordinates"
    assert nangka_coords[0] == 14.6507, "Nangka latitude should be 14.6507"

    unknown_coords = geocoder.get_coordinates("Unknown Location")
    assert unknown_coords is None, "Should not find unknown location"

    logger.info("✅ Geocoding test passed\n")


def test_nlp_geocoding_integration():
    """Test NLP + Geocoding integration."""
    logger.info("\n=== TEST 3: NLP + Geocoding Integration ===")

    nlp = NLPProcessor()
    geocoder = LocationGeocoder()

    test_texts = [
        "Baha sa Nangka! Tuhod level!",
        "Waist deep flood sa SM Marikina",
        "Clear na sa unknown place"
    ]

    enhanced_results = []
    for text in test_texts:
        # Step 1: NLP extraction
        nlp_result = nlp.extract_flood_info(text)

        # Step 2: Geocoding
        enhanced = geocoder.geocode_nlp_result(nlp_result)
        enhanced_results.append(enhanced)

        logger.info(
            f"Text: {text}\n"
            f"  Location: {enhanced.get('location')}\n"
            f"  Has coordinates: {enhanced.get('has_coordinates')}\n"
            f"  Coordinates: {enhanced.get('coordinates')}\n"
        )

    # Assertions
    assert enhanced_results[0]['has_coordinates'], "Nangka should have coordinates"
    assert enhanced_results[0]['coordinates']['lat'] == 14.6507
    assert enhanced_results[1]['has_coordinates'], "SM Marikina should have coordinates"
    assert not enhanced_results[2]['has_coordinates'], "Unknown place should not have coordinates"

    logger.info("✅ NLP + Geocoding integration test passed\n")
    return enhanced_results


def test_hazard_agent_coordinate_methods():
    """Test HazardAgent coordinate-based methods."""
    logger.info("\n=== TEST 4: HazardAgent Coordinate Methods ===")

    # Initialize environment and agent
    # Note: DynamicGraphEnvironment automatically loads graph in __init__
    environment = DynamicGraphEnvironment()

    hazard_agent = HazardAgent("hazard-test", environment)
    # Note: HazardAgent may also load components automatically

    # Test 1: Nearest node finding
    logger.info("\nTest 4.1: Finding nearest node")
    test_lat, test_lon = 14.6507, 121.1009  # Nangka coordinates
    nearest_node = hazard_agent.get_nearest_node(test_lat, test_lon)
    logger.info(f"Nearest node to Nangka ({test_lat}, {test_lon}): {nearest_node}")
    assert nearest_node is not None, "Should find nearest node"

    # Test 2: Distance calculation
    logger.info("\nTest 4.2: Distance calculation")
    lat1, lon1 = 14.6507, 121.1009  # Nangka
    lat2, lon2 = 14.6664, 121.1067  # Concepcion Uno
    distance = hazard_agent.calculate_distance(lat1, lon1, lat2, lon2)
    logger.info(f"Distance from Nangka to Concepcion Uno: {distance:.2f} meters")
    assert 1000 < distance < 3000, f"Distance should be ~1-3km, got {distance}m"

    # Test 3: Nodes within radius
    logger.info("\nTest 4.3: Finding nodes within radius")
    nearby_nodes = hazard_agent.get_nodes_within_radius(test_lat, test_lon, radius_m=500)
    logger.info(f"Found {len(nearby_nodes)} nodes within 500m of Nangka")
    assert len(nearby_nodes) > 0, "Should find nodes within radius"

    # Test 4: Risk update
    logger.info("\nTest 4.4: Updating node risk")
    initial_risks = []
    for u, v, key, data in environment.graph.edges(nearest_node, keys=True, data=True):
        initial_risks.append(data.get('risk_score', 0))

    hazard_agent.update_node_risk(nearest_node, 0.8, source="test")

    updated_risks = []
    for u, v, key, data in environment.graph.edges(nearest_node, keys=True, data=True):
        updated_risks.append(data.get('risk_score', 0))

    logger.info(f"Updated {len(updated_risks)} edges connected to node {nearest_node}")
    logger.info(f"Risk values after update: {updated_risks}")
    assert any(r > 0.5 for r in updated_risks), "Should have high risk edges after update"

    logger.info("✅ HazardAgent coordinate methods test passed\n")


def test_complete_pipeline():
    """Test complete integration pipeline."""
    logger.info("\n=== TEST 5: Complete Integration Pipeline ===")

    # Initialize all components
    nlp = NLPProcessor()
    geocoder = LocationGeocoder()
    environment = DynamicGraphEnvironment()  # Automatically loads graph
    hazard_agent = HazardAgent("hazard-pipeline-test", environment)

    # Load test tweets
    tweets = load_synthetic_tweets("moderate")
    logger.info(f"Loaded {len(tweets)} test tweets")

    # Process tweets through pipeline
    processed_reports = []
    skipped_no_coordinates = 0

    for tweet in tweets[:10]:  # Test with first 10 tweets
        try:
            # Step 1: NLP extraction
            flood_info = nlp.extract_flood_info(tweet['text'])

            # Step 2: Geocoding
            enhanced_info = geocoder.geocode_nlp_result(flood_info)

            # Step 3: Filter and create report
            if enhanced_info['is_flood_related'] and enhanced_info.get('has_coordinates'):
                report = {
                    "location": enhanced_info['location'],
                    "coordinates": enhanced_info['coordinates'],
                    "severity": enhanced_info['severity'],
                    "report_type": enhanced_info['report_type'],
                    "confidence": enhanced_info['confidence'],
                    "timestamp": datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00')),
                    "source": "twitter",
                    "source_url": tweet.get('url', ''),
                    "username": tweet.get('username', ''),
                    "text": tweet['text']
                }
                processed_reports.append(report)
                logger.info(
                    f"✓ Processed: @{tweet.get('username')} - "
                    f"{enhanced_info['location']} "
                    f"({enhanced_info['coordinates']['lat']:.4f}, "
                    f"{enhanced_info['coordinates']['lon']:.4f}) - "
                    f"severity {enhanced_info['severity']:.2f}"
                )
            elif enhanced_info['is_flood_related']:
                skipped_no_coordinates += 1
                logger.info(
                    f"✗ Skipped (no coords): {enhanced_info.get('location')} - "
                    f"{tweet['text'][:50]}..."
                )

        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            continue

    logger.info(
        f"\nProcessing summary: {len(processed_reports)} reports with coordinates, "
        f"{skipped_no_coordinates} skipped (no coordinates)"
    )

    # Step 4: Forward to HazardAgent
    if processed_reports:
        logger.info(f"\nForwarding {len(processed_reports)} reports to HazardAgent...")
        hazard_agent.process_scout_data_with_coordinates(processed_reports)
        logger.info("✓ Reports forwarded and graph updated")

    # Assertions
    assert len(processed_reports) > 0, "Should process at least one report"
    assert all('coordinates' in r for r in processed_reports), "All reports should have coordinates"

    logger.info("✅ Complete pipeline test passed\n")

    return {
        "total_tweets": len(tweets[:10]),
        "processed_reports": len(processed_reports),
        "skipped_no_coordinates": skipped_no_coordinates,
        "reports": processed_reports
    }


def run_all_tests():
    """Run all integration tests."""
    logger.info("=" * 80)
    logger.info("SCOUT AGENT → GEOCODER → HAZARD AGENT INTEGRATION TEST")
    logger.info("=" * 80)

    try:
        # Test 1: NLP extraction
        test_nlp_extraction()

        # Test 2: Geocoding
        test_geocoding()

        # Test 3: NLP + Geocoding
        test_nlp_geocoding_integration()

        # Test 4: HazardAgent coordinate methods
        test_hazard_agent_coordinate_methods()

        # Test 5: Complete pipeline
        results = test_complete_pipeline()

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("ALL TESTS PASSED ✅")
        logger.info("=" * 80)
        logger.info("\nIntegration Test Summary:")
        logger.info(f"  Total tweets processed: {results['total_tweets']}")
        logger.info(f"  Reports with coordinates: {results['processed_reports']}")
        logger.info(f"  Skipped (no coordinates): {results['skipped_no_coordinates']}")
        logger.info(f"  Success rate: {results['processed_reports']/results['total_tweets']*100:.1f}%")

        # Save results
        output_file = Path(__file__).parent / f"integration_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tweets": results['total_tweets'],
                    "processed_reports": results['processed_reports'],
                    "skipped_no_coordinates": results['skipped_no_coordinates']
                },
                "reports": results['reports']
            }, f, indent=2, default=str, ensure_ascii=False)

        logger.info(f"\nDetailed results saved to: {output_file}")

        return True

    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
