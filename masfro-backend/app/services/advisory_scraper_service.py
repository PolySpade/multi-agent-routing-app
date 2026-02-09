
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
import re

logger = logging.getLogger(__name__)

class AdvisoryScraperService:
    """
    Service for discovering and scraping flood advisories from various sources
    (PAGASA, Google News RSS, etc.).
    Includes logic for date filtering to avoid processing stale news.
    """

    def __init__(self, max_age_hours: int = 24, pagasa_url: str = None, rss_url: str = None):
        """
        Initialize AdvisoryScraperService.

        Args:
            max_age_hours: Maximum age of articles to include
            pagasa_url: Override PAGASA base URL (e.g. mock server URL)
            rss_url: Override Google News RSS URL (e.g. mock server URL)
        """
        self.max_age_hours = max_age_hours
        self._pagasa_base_url = pagasa_url or "https://bagong.pagasa.dost.gov.ph"
        self._rss_base_url = rss_url  # None means use Google News

    def discover_pagasa_advisories(self) -> List[str]:
        """
        Dynamically discovers active flood advisory URLs from PAGASA's main flood portal.
        """
        base_url = self._pagasa_base_url
        main_flood_url = f"{base_url}/flood" if "/flood" not in base_url else base_url
        discovered_urls = []

        try:
            logger.info(f"Discovering advisories from {main_flood_url}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(main_flood_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    text = link.get_text().lower()
                    if "flood advisory" in text or "rainfall warning" in text or "flood-bulletin" in href:
                        if href.startswith("http"):
                            full_url = href
                        elif href.startswith("/"):
                            # Absolute path: join with scheme + authority only
                            from urllib.parse import urlparse
                            parsed = urlparse(base_url)
                            full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
                        else:
                            full_url = f"{base_url}/{href}"
                        if full_url not in discovered_urls:
                            discovered_urls.append(full_url)
                            
            logger.info(f"Discovered {len(discovered_urls)} PAGASA URLs")
            return discovered_urls

        except Exception as e:
            logger.error(f"PAGASA discovery failed: {e}")
            return []

    def scrape_google_news_rss(self, query: str) -> List[Dict[str, str]]:
        """
        Scrapes detailed text from Google News RSS feed for a specific query.
        Filters out articles older than self.max_age_hours.
        
        Returns:
            List of dicts: {"text": str, "pub_date": str, "link": str}
        """
        # Use override RSS URL if provided, otherwise default to Google News
        if self._rss_base_url:
            rss_url = f"{self._rss_base_url}?q={query}&hl=en-PH&gl=PH&ceid=PH:en"
        else:
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-PH&gl=PH&ceid=PH:en"
        discovered_items = []
        
        try:
            logger.info(f"Fetching news from RSS: {query}")
            response = requests.get(rss_url, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                now = datetime.now(timezone.utc)
                
                for item in root.findall('./channel/item'):
                    title = item.find('title').text or ""
                    description = item.find('description').text or ""
                    pub_date_str = item.find('pubDate').text or ""
                    link = item.find('link').text or ""
                    
                    # Date Filtering
                    is_current = self._is_recent(pub_date_str, now)
                    if not is_current:
                        continue

                    # Keyword Relevance Check
                    keywords = ["marikina", "water level", "baha", "flood", "warning", "evacuation"]
                    combined_text = f"{title}. {description}"
                    
                    if any(k in combined_text.lower() for k in keywords):
                        clean_text = self._strip_html_tags(combined_text)
                        
                        discovered_items.append({
                            "text": clean_text,
                            "pub_date": pub_date_str,
                            "link": link
                        })
                        
            logger.info(f"Found {len(discovered_items)} relevant and recent articles for '{query}'")
            return discovered_items

        except Exception as e:
            logger.error(f"RSS Scraping failed for {query}: {e}")
            return []

    def _is_recent(self, date_str: str, now: datetime) -> bool:
        """Check if the date string is within the max_age_hours window."""
        # If max_age_hours is 0 or None, filtering is disabled
        if not self.max_age_hours:
            return True

        try:
            if not date_str:
                return False # No date = assume old/invalid
                
            # Parse RFC 2822 date (e.g., Sat, 03 Feb 2026 10:00:00 GMT)
            item_date = parsedate_to_datetime(date_str)
            
            # Ensure item_date is aware if now is aware
            if item_date.tzinfo is None:
                item_date = item_date.replace(tzinfo=timezone.utc)
                
            diff = now - item_date
            
            # Allow some future drift (clock skew) but mainly check past
            if diff.total_seconds() < 0:
                # In the future? Allow if small (e.g. 1 hour), else ignore
                return abs(diff.total_seconds()) < 3600
                
            return diff < timedelta(hours=self.max_age_hours)
            
        except Exception as e:
            logger.debug(f"Date parsing failed for {date_str}: {e}")
            return False

    def _strip_html_tags(self, text: str) -> str:
        """Helper to remove HTML tags from RSS descriptions"""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
