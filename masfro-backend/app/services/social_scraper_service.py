"""
Social Media Scraper Service for MAS-FRO ScoutAgent.

Provides two methods of collecting social media data:
1. scrape_feed() - BeautifulSoup scraping of HTML feed page
2. fetch_tweets_api() - JSON API call for structured tweet data

Both methods return data in the scout_tweets format compatible
with ScoutAgent's existing _process_and_forward_tweets() pipeline.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SocialScraperService:
    """
    Service for scraping social media data from the mock server
    (or any compatible social feed endpoint).

    Supports two data collection modes:
    - HTML scraping via BeautifulSoup (scrape_feed)
    - JSON API fetching (fetch_tweets_api)
    """

    def __init__(self, base_url: str = "http://localhost:8081"):
        """
        Initialize the social scraper service.

        Args:
            base_url: Base URL of the social media server (mock or real)
        """
        self.base_url = base_url.rstrip("/")
        self.feed_url = f"{self.base_url}/social/feed"
        self.api_url = f"{self.base_url}/social/api/tweets"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self._mock_down = False
        self._mock_down_logged = False
        self._last_check_time = 0.0
        self._backoff_seconds = 60.0  # retry mock server every 60s when down
        logger.info(f"SocialScraperService initialized with base_url={self.base_url}")

    def scrape_feed(self) -> List[Dict[str, Any]]:
        """
        BeautifulSoup scrapes HTML at /social/feed.
        Parses article.tweet elements and returns data in scout_tweets format.

        Returns:
            List of tweet dictionaries compatible with ScoutAgent processing.
        """
        try:
            # Skip if mock server is known to be down (backoff)
            if self._mock_down:
                if time.time() - self._last_check_time < self._backoff_seconds:
                    return []
                # Retry after backoff
                logger.debug(f"Retrying social feed after backoff...")

            response = requests.get(self.feed_url, headers=self.headers, timeout=5)
            response.raise_for_status()

            # Server is back up
            if self._mock_down:
                logger.info(f"Mock social server is back online at {self.feed_url}")
                self._mock_down = False
                self._mock_down_logged = False

            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("article", class_="tweet")

            tweets = []
            for article in articles:
                tweet_id = article.get("data-tweet-id", "")

                username_el = article.find("span", class_="username")
                username = username_el.get_text(strip=True).lstrip("@") if username_el else ""

                timestamp_el = article.find("time", class_="timestamp")
                timestamp = timestamp_el.get("datetime", "") if timestamp_el else ""

                text_el = article.find("div", class_="tweet-text")
                text = text_el.get_text(strip=True) if text_el else ""

                # Media
                image_path = None
                media_el = article.find("div", class_="tweet-media")
                if media_el:
                    img = media_el.find("img")
                    if img:
                        image_path = img.get("src")

                # Stats
                replies = "0"
                retweets = "0"
                likes = "0"

                replies_el = article.find("span", class_="replies")
                if replies_el:
                    replies = replies_el.get_text(strip=True)

                retweets_el = article.find("span", class_="retweets")
                if retweets_el:
                    retweets = retweets_el.get_text(strip=True)

                likes_el = article.find("span", class_="likes")
                if likes_el:
                    likes = likes_el.get_text(strip=True)

                tweet = {
                    "tweet_id": tweet_id,
                    "username": username,
                    "text": text,
                    "timestamp": timestamp,
                    "url": f"https://x.com/{username}/status/{tweet_id}",
                    "image_path": image_path,
                    "replies": replies,
                    "retweets": retweets,
                    "likes": likes,
                    "scraped_at": datetime.now().isoformat(),
                }
                tweets.append(tweet)

            logger.info(f"Scraped {len(tweets)} tweets from social feed")
            return tweets

        except requests.exceptions.ConnectionError:
            self._last_check_time = time.time()
            if not self._mock_down_logged:
                logger.warning(
                    f"Mock social server unavailable at {self.feed_url} "
                    f"- will retry every {int(self._backoff_seconds)}s silently"
                )
                self._mock_down_logged = True
            self._mock_down = True
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to scrape social feed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing social feed: {e}")
            return []

    def fetch_tweets_api(self, limit: int = 50, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        JSON API call to /social/api/tweets.
        Returns data in scout_tweets format.

        Args:
            limit: Maximum number of tweets to fetch
            since: ISO timestamp to filter tweets after

        Returns:
            List of tweet dictionaries compatible with ScoutAgent processing.
        """
        try:
            # Skip if mock server is known to be down (backoff)
            if self._mock_down:
                if time.time() - self._last_check_time < self._backoff_seconds:
                    return []

            params = {"limit": limit}
            if since:
                params["since"] = since

            response = requests.get(
                self.api_url, params=params, headers=self.headers, timeout=5
            )
            response.raise_for_status()

            data = response.json()
            tweets = data.get("tweets", [])

            # Ensure each tweet has scraped_at timestamp
            for tweet in tweets:
                if "scraped_at" not in tweet:
                    tweet["scraped_at"] = datetime.now().isoformat()

            logger.info(f"Fetched {len(tweets)} tweets from API")
            return tweets

        except requests.exceptions.ConnectionError:
            self._last_check_time = time.time()
            self._mock_down = True
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tweets API: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing tweets API response: {e}")
            return []
