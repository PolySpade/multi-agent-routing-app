"""
Synthetic Data Generator for Scout Agent
-----------------------------------------
Generates realistic synthetic Twitter/X data for testing the Scout Agent's
flood monitoring capabilities in Marikina City.

Usage:
    python scripts/generate_scout_synthetic_data.py
"""

import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Marikina locations (actual barangays and landmarks)
MARIKINA_LOCATIONS = [
    "Nangka", "Sto Nino", "Tumana", "Malanday", "Concepcion",
    "Parang", "Kalumpang", "Industrial Valley", "SM Marikina",
    "Riverbanks", "Marcos Highway", "Gil Fernando", "J.P. Rizal",
    "Marikina Bridge", "Loyola Heights border"
]

# Realistic Twitter usernames
USERNAMES = [
    "marikina_alert", "baranggay_watch", "marikinaresident",
    "floodwatch_ph", "mmda_updates", "pagasa_updates",
    "concerned_citizen", "marikina_news", "barangay_nangka",
    "residents_ph", "traffic_alert", "weather_ph",
    "manila_bulletin", "inquirer_news", "cnn_ph",
    "abs_cbn_news", "rappler", "marikina_lgu"
]

# Tweet templates by severity level
TWEET_TEMPLATES = {
    "minor": [
        "Light rain in {location}. Streets are wet but passable. #MarikinaWeather",
        "Drizzle in {location} area. No flooding yet. Stay safe everyone! #Marikina",
        "Starting to rain in {location}. Monitoring the situation. #MarikinaUpdates",
        "Ulan sa {location}. Konti lang naman. Normal traffic flow pa.",
        "Small puddles forming in {location}. Nothing serious for now.",
    ],
    "moderate": [
        "Moderate rain in {location}! Water starting to rise near the riverbanks. #MarikinaFlood",
        "Baha na sa {location}! Ankle-deep water on some streets. Drive carefully!",
        "Flooding in {location} area. Water level rising. Avoid if possible. #Marikina",
        "Heavy rain in {location}. Some streets already flooded. #MarikinaFlood #UpdatesPH",
        "{location} residents, prepare! Water rising fast. #FloodAlert",
        "Tumataas na tubig sa {location}. Knee-deep na sa ilang bahagi. #MarikinaAlert",
    ],
    "severe": [
        "CRITICAL: Severe flooding in {location}! Water waist-deep. Evacuate now! #MarikinaFlood",
        "⚠️ FLOOD ALERT: {location} heavily flooded! Residents evacuating. #Marikina #Emergency",
        "URGENT: {location} underwater! Rescue operations ongoing! #MarikinaFlood #Emergency",
        "🚨 {location} residents evacuating! Water level critical! #MarikinaFlood",
        "BREAKING: Massive flooding in {location}. Roads impassable. Stay safe! #Marikina",
        "Malubhang baha sa {location}! Hanggang dibdib na ang tubig! #MarikinaFlood",
    ],
    "rain_only": [
        "Heavy rain in Marikina now. Everybody be careful! #Ulan #MarikinaWeather",
        "Non-stop rain since this morning in {location}. #MarikinaRain",
        "It's raining hard in {location}. Traffic slower than usual.",
        "Malakas ang ulan dito sa {location}. Ingat sa mga motorista!",
    ]
}

# Report types based on tweet content
REPORT_TYPES = [
    "flood_observation",
    "flood_warning",
    "rain_report",
    "water_level_update",
    "evacuation_notice",
    "traffic_update"
]


def generate_tweet_id(username: str, text: str, timestamp: str) -> str:
    """Generate a unique tweet ID (simulates Twitter's ID system)."""
    unique_string = f"{username}_{text}_{timestamp}"
    hash_obj = hashlib.md5(unique_string.encode('utf-8'))
    # Twitter IDs are numeric, so we convert hash to int
    return str(int(hash_obj.hexdigest()[:16], 16))


def generate_synthetic_tweet(
    severity_level: str,
    base_time: datetime,
    time_offset_minutes: int
) -> Dict[str, Any]:
    """
    Generate a single synthetic tweet.

    Args:
        severity_level: "minor", "moderate", "severe", or "rain_only"
        base_time: Base timestamp for the event
        time_offset_minutes: Minutes to add to base_time

    Returns:
        Dictionary with tweet data
    """
    location = random.choice(MARIKINA_LOCATIONS)
    username = random.choice(USERNAMES)
    template = random.choice(TWEET_TEMPLATES[severity_level])
    text = template.format(location=location)

    # Add realistic timestamp
    tweet_time = base_time + timedelta(minutes=time_offset_minutes)
    timestamp = tweet_time.isoformat() + "Z"

    # Generate realistic engagement metrics (higher for severe floods)
    base_engagement = {
        "minor": (5, 50),
        "moderate": (20, 200),
        "severe": (100, 1000),
        "rain_only": (10, 100)
    }
    min_eng, max_eng = base_engagement[severity_level]

    replies = str(random.randint(min_eng // 10, max_eng // 10))
    retweets = str(random.randint(min_eng // 5, max_eng // 5))
    likes = str(random.randint(min_eng, max_eng))

    # Create tweet ID
    tweet_id = generate_tweet_id(username, text, timestamp)
    url = f"https://x.com/{username}/status/{tweet_id}"

    # Scraped time (a few seconds after tweet time)
    scraped_time = tweet_time + timedelta(seconds=random.randint(10, 300))

    return {
        "tweet_id": tweet_id,
        "username": username,
        "text": text,
        "timestamp": timestamp,
        "url": url,
        "replies": replies,
        "retweets": retweets,
        "likes": likes,
        "scraped_at": scraped_time.isoformat(),
        # Ground truth labels (for testing NLP processor)
        "_ground_truth": {
            "location": location,
            "severity_level": severity_level,
            "is_flood_related": severity_level != "rain_only"
        }
    }


def generate_processed_report(tweet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate the processed report that HazardAgent would receive.
    This simulates what the NLP processor outputs.

    Args:
        tweet: Raw tweet data

    Returns:
        Processed report dictionary
    """
    ground_truth = tweet["_ground_truth"]

    # Map severity level to numeric severity (0.0 - 1.0)
    severity_mapping = {
        "minor": random.uniform(0.1, 0.3),
        "moderate": random.uniform(0.4, 0.6),
        "severe": random.uniform(0.7, 1.0),
        "rain_only": random.uniform(0.0, 0.2)
    }

    # Determine report type based on content
    report_type_mapping = {
        "minor": "rain_report",
        "moderate": "flood_observation",
        "severe": "evacuation_notice",
        "rain_only": "rain_report"
    }

    # Confidence varies (higher for clear reports)
    confidence_mapping = {
        "minor": random.uniform(0.6, 0.8),
        "moderate": random.uniform(0.7, 0.9),
        "severe": random.uniform(0.8, 0.95),
        "rain_only": random.uniform(0.5, 0.7)
    }

    severity_level = ground_truth["severity_level"]

    return {
        "location": ground_truth["location"],
        "severity": round(severity_mapping[severity_level], 2),
        "report_type": report_type_mapping[severity_level],
        "confidence": round(confidence_mapping[severity_level], 2),
        "timestamp": tweet["timestamp"],
        "source": "twitter",
        "source_url": tweet["url"],
        "username": tweet["username"],
        "text": tweet["text"]
    }


def generate_flood_scenario(
    scenario_name: str,
    num_tweets: int = 50,
    start_time: datetime = None
) -> Dict[str, Any]:
    """
    Generate a complete flood scenario with tweets over time.

    Args:
        scenario_name: Name/description of the scenario
        num_tweets: Number of tweets to generate
        start_time: Starting time for the scenario

    Returns:
        Dictionary with scenario metadata and tweets
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=2)

    tweets = []
    processed_reports = []

    # Simulate realistic flood progression over time
    # Early tweets: mostly rain reports
    # Middle tweets: moderate flooding
    # Late tweets: severe flooding (if applicable)

    for i in range(num_tweets):
        # Determine severity based on time progression
        progress = i / num_tweets

        if progress < 0.3:
            # Early phase: mostly rain, some minor flooding
            severity = random.choice(["rain_only", "rain_only", "minor"])
        elif progress < 0.7:
            # Middle phase: moderate flooding
            severity = random.choice(["minor", "moderate", "moderate"])
        else:
            # Late phase: severe flooding
            severity = random.choice(["moderate", "severe", "severe"])

        # Generate tweet with realistic time offset
        time_offset = int(progress * 180)  # Spread over 3 hours
        tweet = generate_synthetic_tweet(severity, start_time, time_offset)
        tweets.append(tweet)

        # Generate processed report if flood-related
        if tweet["_ground_truth"]["is_flood_related"]:
            report = generate_processed_report(tweet)
            processed_reports.append(report)

    return {
        "scenario_name": scenario_name,
        "start_time": start_time.isoformat(),
        "duration_hours": 3,
        "total_tweets": len(tweets),
        "flood_related_tweets": len(processed_reports),
        "tweets": tweets,
        "processed_reports": processed_reports
    }


def main():
    """Generate and save synthetic scout data."""
    print("=== Generating Synthetic Scout Agent Data ===\n")

    # Generate multiple scenarios
    scenarios = [
        generate_flood_scenario(
            "Typhoon Scenario - Heavy Flooding",
            num_tweets=100,
            start_time=datetime(2025, 11, 13, 8, 0, 0)
        ),
        generate_flood_scenario(
            "Monsoon Rain - Moderate Flooding",
            num_tweets=50,
            start_time=datetime(2025, 11, 12, 14, 0, 0)
        ),
        generate_flood_scenario(
            "Light Rain - Minimal Impact",
            num_tweets=30,
            start_time=datetime(2025, 11, 11, 10, 0, 0)
        )
    ]

    # Save to JSON files
    output_dir = "app/data/synthetic"
    import os
    os.makedirs(output_dir, exist_ok=True)

    for i, scenario in enumerate(scenarios, 1):
        # Save complete scenario
        scenario_file = f"{output_dir}/scout_scenario_{i}_{scenario['scenario_name'].replace(' ', '_').lower()}.json"
        with open(scenario_file, 'w', encoding='utf-8') as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved: {scenario_file}")

        # Save just the tweets (in master format)
        tweets_file = f"{output_dir}/scout_tweets_{i}.json"
        tweets_dict = {tweet["tweet_id"]: tweet for tweet in scenario["tweets"]}
        with open(tweets_file, 'w', encoding='utf-8') as f:
            json.dump(tweets_dict, f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved: {tweets_file}")

        # Save processed reports (what HazardAgent receives)
        reports_file = f"{output_dir}/scout_reports_{i}.json"
        with open(reports_file, 'w', encoding='utf-8') as f:
            json.dump(scenario["processed_reports"], f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved: {reports_file}")

    # Generate summary statistics
    total_tweets = sum(s["total_tweets"] for s in scenarios)
    total_flood_related = sum(s["flood_related_tweets"] for s in scenarios)

    print(f"\n=== Summary ===")
    print(f"   Total scenarios: {len(scenarios)}")
    print(f"   Total tweets: {total_tweets}")
    print(f"   Flood-related: {total_flood_related} ({total_flood_related/total_tweets*100:.1f}%)")

    # Save summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "scenarios": [
            {
                "name": s["scenario_name"],
                "tweets": s["total_tweets"],
                "flood_related": s["flood_related_tweets"],
                "start_time": s["start_time"]
            }
            for s in scenarios
        ],
        "total_tweets": total_tweets,
        "total_flood_related": total_flood_related
    }

    summary_file = f"{output_dir}/scout_data_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"[OK] Saved summary: {summary_file}")

    print("\n=== Synthetic data generation complete! ===")


if __name__ == "__main__":
    main()
