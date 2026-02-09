#!/usr/bin/env python3
# filename: scripts/generate_synthetic_data.py

"""
Synthetic Data Generator for ScoutAgent

Generates realistic synthetic flood report tweets with optional image references
for testing the ScoutAgent pipeline. Includes ground truth labels for evaluation.

Features:
- Multiple flood scenarios (light, moderate, heavy)
- Image path references for visual analysis testing
- Ground truth labels for ML evaluation
- Realistic Filipino/English mixed language
- Marikina-specific locations and landmarks

Usage:
    python scripts/generate_synthetic_data.py --scenario 1 --with-images
    python scripts/generate_synthetic_data.py --all

Author: MAS-FRO Development Team
Date: February 2026
"""

import json
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


# Marikina locations for flood reports
MARIKINA_LOCATIONS = [
    "J.P. Rizal", "Shoe Ave", "Riverbanks", "Sto. Nino", "SM Marikina",
    "Marikina Sports Center", "Concepcion", "Nangka", "Tumana", "Malanday",
    "Industrial Valley", "Kalumpang", "Parang", "Marcos Highway",
    "Gil Fernando", "Marikina Bridge", "Loyola Heights border"
]

# Twitter-style usernames
USERNAMES = [
    "marikina_news", "weather_ph", "flood_watch_ph", "mmda_updates",
    "pagasa_updates", "traffic_alert", "concerned_citizen", "marikina_lgu",
    "barangay_nangka", "barangay_watch", "marikinaresident", "floodwatch_ph",
    "residents_ph", "marikina_alert", "rappler", "inquirer_news",
    "abs_cbn_news", "gma_news", "cnn_ph", "manila_bulletin"
]

# Tweet templates by severity
TWEET_TEMPLATES = {
    "rain_only": [
        "Light rain in {location}. Streets are wet but passable. #MarikinaWeather",
        "Drizzle in {location} area. No flooding yet. Stay safe everyone! #Marikina",
        "Starting to rain in {location}. Monitoring the situation. #MarikinaUpdates",
        "Ulan sa {location}. Konti lang naman. Normal traffic flow pa.",
        "It's raining hard in {location}. Traffic slower than usual.",
        "Heavy rain in Marikina now. Everybody be careful! #Ulan #MarikinaWeather",
        "Malakas ang ulan dito sa {location}. Ingat sa mga motorista!",
        "Non-stop rain since this morning in {location}. #MarikinaRain"
    ],
    "minor": [
        "Small puddles forming in {location}. Nothing serious for now.",
        "Water starting to accumulate in {location}. Be careful drivers!",
        "Minor flooding in low-lying areas of {location}. Still passable.",
        "Konting baha sa {location}. Passable pa naman for cars.",
        "Water on the road at {location}. Slow down when passing."
    ],
    "moderate": [
        "Flooding in {location} area. Water level rising. Avoid if possible. #Marikina",
        "Moderate rain in {location}! Water starting to rise near the riverbanks. #MarikinaFlood",
        "Heavy rain in {location}. Some streets already flooded. #MarikinaFlood #UpdatesPH",
        "Baha na sa {location}! Ankle-deep water on some streets. Drive carefully!",
        "Tumataas na tubig sa {location}. Knee-deep na sa ilang bahagi. #MarikinaAlert",
        "{location} residents, prepare! Water rising fast. #FloodAlert"
    ],
    "severe": [
        "BREAKING: Massive flooding in {location}. Roads impassable. Stay safe! #Marikina",
        "URGENT: {location} underwater! Rescue operations ongoing! #MarikinaFlood #Emergency",
        "CRITICAL: Severe flooding in {location}! Water waist-deep. Evacuate now! #MarikinaFlood",
        "Riverbanks overflowing at {location}! Mandatory evacuation in effect!",
        "Flood ALERT: {location} residents evacuating! Water level critical! #MarikinaFlood",
        "FLOOD ALERT: {location} heavily flooded! Residents evacuating. #Marikina #Emergency"
    ]
}

# Image filename patterns by severity
IMAGE_PATTERNS = {
    "minor": ["ankle_deep_01.jpg", "ankle_deep_02.jpg", "ankle_deep_03.jpg"],
    "moderate": ["knee_deep_01.jpg", "knee_deep_02.jpg", "knee_deep_03.jpg"],
    "severe": ["waist_deep_01.jpg", "waist_deep_02.jpg", "chest_deep_01.jpg"]
}


class SyntheticDataGenerator:
    """Generates synthetic flood report tweets for ScoutAgent testing."""

    def __init__(self, scenario: int = 1, include_images: bool = True):
        """
        Initialize the generator.

        Args:
            scenario: Flood scenario (1=heavy, 2=moderate, 3=light)
            include_images: Whether to include image path references
        """
        self.scenario = scenario
        self.include_images = include_images
        self.image_base_path = "app/data/sample_images/flood_levels"

        # Scenario configurations
        self.scenario_configs = {
            1: {  # Heavy flooding (typhoon)
                "name": "Typhoon Scenario - Heavy Flooding",
                "duration_hours": 6,
                "tweet_count": 100,
                "severity_weights": {
                    "rain_only": 0.15,
                    "minor": 0.20,
                    "moderate": 0.35,
                    "severe": 0.30
                },
                "image_probability": 0.4
            },
            2: {  # Moderate flooding (monsoon)
                "name": "Monsoon Rain - Moderate Flooding",
                "duration_hours": 4,
                "tweet_count": 75,
                "severity_weights": {
                    "rain_only": 0.25,
                    "minor": 0.35,
                    "moderate": 0.30,
                    "severe": 0.10
                },
                "image_probability": 0.3
            },
            3: {  # Light rain (minimal flooding)
                "name": "Light Rain - Minimal Impact",
                "duration_hours": 3,
                "tweet_count": 50,
                "severity_weights": {
                    "rain_only": 0.50,
                    "minor": 0.35,
                    "moderate": 0.12,
                    "severe": 0.03
                },
                "image_probability": 0.15
            }
        }

    def generate_tweets(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate synthetic tweets for the configured scenario.

        Returns:
            Dict mapping tweet_id to tweet data
        """
        config = self.scenario_configs[self.scenario]
        tweets = {}

        start_time = datetime(2025, 11, 13, 8, 0, 0)
        duration = timedelta(hours=config["duration_hours"])
        tweet_count = config["tweet_count"]

        # Calculate time interval between tweets
        interval = duration / tweet_count

        for i in range(tweet_count):
            tweet_time = start_time + (interval * i)
            tweet = self._generate_single_tweet(tweet_time, config)
            tweets[tweet["tweet_id"]] = tweet

        return tweets

    def _generate_single_tweet(
        self,
        timestamp: datetime,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a single synthetic tweet."""
        # Select severity based on weights
        severity = self._weighted_choice(config["severity_weights"])

        # Select location
        location = random.choice(MARIKINA_LOCATIONS)

        # Generate tweet text
        template = random.choice(TWEET_TEMPLATES[severity])
        text = template.format(location=location)

        # Add emoji for severe tweets
        if severity == "severe":
            emojis = ["", "", "", ""]
            text = random.choice(emojis) + " " + text

        # Generate tweet metadata
        tweet_id = str(random.randint(10**17, 10**19))
        username = random.choice(USERNAMES)

        tweet = {
            "tweet_id": tweet_id,
            "username": username,
            "text": text,
            "timestamp": timestamp.isoformat() + "Z",
            "url": f"https://x.com/{username}/status/{tweet_id}",
            "replies": str(random.randint(0, 20)),
            "retweets": str(random.randint(0, 40)),
            "likes": str(random.randint(5, 200)),
            "scraped_at": (timestamp + timedelta(seconds=random.randint(30, 300))).strftime("%Y-%m-%dT%H:%M:%S"),
            "_ground_truth": {
                "location": location,
                "severity_level": severity,
                "is_flood_related": severity != "rain_only"
            }
        }

        # Add image path for flood-related tweets
        if self.include_images and severity != "rain_only":
            if random.random() < config["image_probability"]:
                image_file = random.choice(IMAGE_PATTERNS.get(severity, IMAGE_PATTERNS["moderate"]))
                tweet["image_path"] = f"{self.image_base_path}/{image_file}"
                tweet["_ground_truth"]["has_image"] = True
            else:
                tweet["_ground_truth"]["has_image"] = False
        else:
            tweet["_ground_truth"]["has_image"] = False

        return tweet

    def _weighted_choice(self, weights: Dict[str, float]) -> str:
        """Select an item based on weights."""
        items = list(weights.keys())
        probabilities = list(weights.values())
        return random.choices(items, probabilities)[0]

    def save_tweets(self, output_dir: Path) -> Path:
        """
        Generate and save tweets to JSON file.

        Args:
            output_dir: Directory to save the output file

        Returns:
            Path to the saved file
        """
        tweets = self.generate_tweets()
        config = self.scenario_configs[self.scenario]

        output_file = output_dir / f"scout_tweets_{self.scenario}.json"
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(tweets, f, indent=2, ensure_ascii=False)

        print(f"Generated {len(tweets)} tweets for scenario {self.scenario}")
        print(f"  Scenario: {config['name']}")
        print(f"  Duration: {config['duration_hours']} hours")
        print(f"  Images included: {self.include_images}")
        print(f"  Saved to: {output_file}")

        # Count by severity
        severity_counts = {}
        image_count = 0
        for tweet in tweets.values():
            sev = tweet["_ground_truth"]["severity_level"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            if tweet.get("image_path"):
                image_count += 1

        print(f"\n  Severity distribution:")
        for sev, count in sorted(severity_counts.items()):
            print(f"    {sev}: {count}")
        print(f"  Tweets with images: {image_count}")

        return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic flood report data for ScoutAgent"
    )
    parser.add_argument(
        "--scenario", "-s",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Scenario to generate (1=heavy, 2=moderate, 3=light)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Generate all scenarios"
    )
    parser.add_argument(
        "--with-images",
        action="store_true",
        default=True,
        help="Include image path references (default: True)"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Exclude image path references"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory (default: app/data/synthetic)"
    )

    args = parser.parse_args()

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Find project root
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / "app" / "data" / "synthetic"

    include_images = not args.no_images

    if args.all:
        scenarios = [1, 2, 3]
    else:
        scenarios = [args.scenario]

    print(f"\n{'='*60}")
    print("MAS-FRO Synthetic Data Generator")
    print(f"{'='*60}\n")

    for scenario in scenarios:
        generator = SyntheticDataGenerator(
            scenario=scenario,
            include_images=include_images
        )
        generator.save_tweets(output_dir)
        print()

    print(f"{'='*60}")
    print("Generation complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
