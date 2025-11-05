# filename: app/agents/scout_agent.py

import time
import os
import json
import pickle
import hashlib
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)

class ScoutAgent(BaseAgent):
    """
    The ScoutAgent is responsible for scraping real-time data from social media
    (X.com/Twitter) to identify flood-related events in Marikina City.

    This agent collects crowdsourced Volunteered Geographic Information (VGI)
    from social media, processes it using NLP, and forwards validated reports
    to the HazardAgent for data fusion.

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        hazard_agent: Reference to HazardAgent for data forwarding
        nlp_processor: NLP processor for tweet analysis
        email: Twitter/X account email
        password: Twitter/X account password
    """
    def __init__(self, agent_id: str, environment, email: str, password: str, hazard_agent=None):
        super().__init__(agent_id, environment)
        self.email = email
        self.password = password
        self.driver = None
        self.hazard_agent = hazard_agent

        # Initialize NLP processor
        try:
            from ..ml_models.nlp_processor import NLPProcessor
            self.nlp_processor = NLPProcessor()
            logger.info(f"{self.agent_id} initialized with NLP processor")
        except Exception as e:
            logger.warning(f"{self.agent_id} failed to initialize NLP processor: {e}")
            self.nlp_processor = None
        
        # --- CENTRALIZED FILE PATHS ---
        # Define the path to the data directory relative to the project root.
        data_directory = os.path.join("app", "data")
        
        # Set the full path for the master tweet file.
        self.master_file = os.path.join(data_directory, "marikina_tweets_master.json")
        
        # NEW: Set the full path for the Twitter session file.
        self.session_file = os.path.join(data_directory, "twitter_session.pkl")
        
        self.master_tweets = {}
        print(f"ScoutAgent '{self.agent_id}' initialized.")
        print(f"  -> Master tweet file path: {self.master_file}")
        print(f"  -> Session file path: {self.session_file}")

    def set_hazard_agent(self, hazard_agent) -> None:
        """
        Set reference to HazardAgent for data forwarding.

        Args:
            hazard_agent: HazardAgent instance
        """
        self.hazard_agent = hazard_agent
        logger.info(f"{self.agent_id} linked to {hazard_agent.agent_id}")

    def setup(self) -> bool:
        """
        Initializes the Selenium WebDriver and logs into X.com.
        This should be called once before the agent starts its monitoring cycle.

        Returns:
            bool: True if setup and login were successful, False otherwise.
        """
        print(f"[{self.agent_id}] Setting up WebDriver and logging in...")
        self.driver = self._login_to_twitter()
        if self.driver:
            self.master_tweets = self._load_master_tweets()
            return True
        return False


    def step(self) -> list:
        """
        Performs one cycle of the agent's primary task: searching for,
        extracting, and processing new tweets. This method is designed to be
        called repeatedly by the main simulation loop.

        Returns:
            list: A list of newly found tweet dictionaries.
        """
        print(f"\n[{self.agent_id}] Performing step at {datetime.now().strftime('%H:%M:%S')}")

        # 1. Search for recent tweets
        raw_tweets = self._search_tweets()

        # 2. Add new tweets to our master list and get only the new ones back
        newly_added_tweets = self._add_new_tweets_to_master(raw_tweets)

        if newly_added_tweets:
            print(f"[{self.agent_id}] Found {len(newly_added_tweets)} new tweets.")

            # 3. Process tweets with NLP and forward to HazardAgent
            self._process_and_forward_tweets(newly_added_tweets)
        else:
            print(f"[{self.agent_id}] No new tweets found in this step.")

        return newly_added_tweets

    def _process_and_forward_tweets(self, tweets: list) -> None:
        """
        Process tweets using NLP and forward to HazardAgent.

        Args:
            tweets: List of tweet dictionaries to process
        """
        if not self.nlp_processor:
            logger.warning(f"{self.agent_id} has no NLP processor, skipping tweet processing")
            return

        if not self.hazard_agent:
            logger.warning(f"{self.agent_id} has no HazardAgent reference, data not forwarded")
            return

        processed_reports = []

        for tweet in tweets:
            try:
                # Extract flood info using NLP
                flood_info = self.nlp_processor.extract_flood_info(tweet['text'])

                if flood_info['is_flood_related']:
                    # Create scout report for HazardAgent
                    report = {
                        "location": flood_info['location'] or "Marikina",  # Default to Marikina
                        "severity": flood_info['severity'],
                        "report_type": flood_info['report_type'],
                        "confidence": flood_info['confidence'],
                        "timestamp": datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00')),
                        "source": "twitter",
                        "source_url": tweet.get('url', ''),
                        "username": tweet.get('username', ''),
                        "text": tweet['text']
                    }

                    processed_reports.append(report)
                    logger.debug(
                        f"{self.agent_id} processed tweet from @{tweet.get('username')}: "
                        f"{flood_info['location']} - severity {flood_info['severity']:.2f}"
                    )

            except Exception as e:
                logger.error(f"{self.agent_id} error processing tweet: {e}")
                continue

        # Forward all processed reports to HazardAgent
        if processed_reports:
            logger.info(
                f"{self.agent_id} forwarding {len(processed_reports)} "
                f"flood reports to HazardAgent"
            )
            self.hazard_agent.process_scout_data(processed_reports)

    def shutdown(self):
        """
        Gracefully closes the Selenium WebDriver and performs any final cleanup.
        """
        print(f"[{self.agent_id}] Shutting down...")
        if self.driver:
            self.driver.quit()
            print(f"[{self.agent_id}] WebDriver closed.")
        self._export_master_tweets_to_csv()

    # --- PRIVATE HELPER METHODS (from your original script) ---
    # The following methods are encapsulated within the agent class.

    def _login_to_twitter(self, use_saved_session=True):
        """
        Logs into Twitter/X.com using Selenium. Attempts to restore a saved session
        first, then performs a fresh login if needed.
        
        Returns:
            WebDriver instance if successful, None otherwise.
        """
        chrome_options = Options()
        # Standard options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Anti-bot detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        custom_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        chrome_options.add_argument(f'user-agent={custom_user_agent}')

        # Experimental options to make it look less like a bot
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()

        try:
            # Try to restore saved session first
            if use_saved_session and self._load_cookies():
                if self._verify_login_status():
                    print(f"[{self.agent_id}] Successfully restored session.")
                    return self.driver
            
            # Perform fresh login
            print(f"[{self.agent_id}] Performing fresh login...")
            self.driver.get("https://x.com/i/flow/login")
            
            # Wait for and enter email/username
            print(f"[{self.agent_id}] Entering email...")
            email_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            email_input.send_keys(self.email)
            email_input.send_keys(Keys.RETURN)
            time.sleep(2)
            
            # Sometimes Twitter asks for username verification (unusual activity)
            try:
                print(f"[{self.agent_id}] Checking for username verification prompt...")
                username_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']"))
                )
                # Extract username from email (assumes email format: username@domain.com)
                username = self.email.split('@')[0]
                username_input.send_keys(username)
                username_input.send_keys(Keys.RETURN)
                time.sleep(2)
                print(f"[{self.agent_id}] Username verification completed.")
            except TimeoutException:
                print(f"[{self.agent_id}] No username verification required.")
            
            # Wait for and enter password
            print(f"[{self.agent_id}] Entering password...")
            password_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
            )
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            
            # Wait for successful login (home timeline appears)
            print(f"[{self.agent_id}] Waiting for login to complete...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Home timeline']"))
            )
            
            print(f"[{self.agent_id}] Fresh login successful!")
            self._save_cookies()
            return self.driver
            
        except Exception as e:
            print(f"[{self.agent_id}] An error occurred during login: {e}")
            if self.driver:
                self.driver.quit()
            self.driver = None
            return None


    def _search_tweets(self, search_url=None):
        """
        Searches for tweets, scrolls to load more, and triggers extraction.
        """
        if search_url is None:
            date = datetime.now().strftime("%Y-%m-%d")
            search_url = f'https://x.com/search?q=%22Marikina%22%20(Baha%20OR%20Flood%20OR%20Ulan%20OR%20Rain%20OR%20pagbaha%20OR%20%22heavy%20rain%22%20OR%20%22water%20level%22)%20since:2025-10-01&f=live'

        try:
            print(f"[{self.agent_id}] Navigating to search URL...")
            self.driver.get(search_url)
            
            # Wait for at least one tweet to appear
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweet']"))
            )
            print(f"[{self.agent_id}] Search results loaded.")
            
            # Scroll down to load more tweets from the dynamic feed
            print(f"[{self.agent_id}] Scrolling to load more tweets...")
            for i in range(3): # Scroll 3 times
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='tweet']")
            print(f"[{self.agent_id}] Found {len(tweet_elements)} tweet elements on page.")
            
            extracted_tweets = [self._extract_tweet_data(t) for t in tweet_elements]
            return [t for t in extracted_tweets if t]  # Filter out None values

        except TimeoutException:
            print(f"[{self.agent_id}] No tweets found on page or page took too long to load.")
            return []
        except Exception as e:
            print(f"[{self.agent_id}] Error during tweet search: {e}")
            return []

    def _extract_tweet_data(self, tweet_element):
        """
        Extracts detailed information from a single Selenium WebElement for a tweet.
        """
        try:
            data = {}
            # Extract username, text, timestamp, URL, and engagement metrics
            data['username'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='User-Name'] a").get_attribute('href').split('/')[-1]
            data['text'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']").text
            time_element = tweet_element.find_element(By.CSS_SELECTOR, "time")
            data['timestamp'] = time_element.get_attribute('datetime')
            data['url'] = time_element.find_element(By.XPATH, "..").get_attribute('href')
            
            # Engagement metrics can sometimes be absent
            try:
                data['replies'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='reply']").text or "0"
            except NoSuchElementException:
                data['replies'] = "0"
            try:
                data['retweets'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='retweet']").text or "0"
            except NoSuchElementException:
                data['retweets'] = "0"
            try:
                data['likes'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='like']").text or "0"
            except NoSuchElementException:
                data['likes'] = "0"
            
            return data
        except Exception:
            # This can happen with ads or other non-standard tweet elements
            return None

    def _add_new_tweets_to_master(self, new_tweets):
        """
        Adds new tweets to the master list, checking for duplicates.
        """
        newly_added = []
        for tweet in new_tweets:
            tweet_id = self._create_tweet_id(tweet)
            if tweet_id not in self.master_tweets:
                tweet['scraped_at'] = datetime.now().isoformat()
                tweet['tweet_id'] = tweet_id
                self.master_tweets[tweet_id] = tweet
                newly_added.append(tweet)
        
        if newly_added:
            self._save_master_tweets()
        return newly_added

    def _create_tweet_id(self, tweet_data):
        """
        Creates a unique ID for a tweet, prioritizing the ID from the URL.
        """
        # The most reliable ID is the numerical string at the end of the URL
        if tweet_data.get('url') and 'status' in tweet_data['url']:
            return tweet_data['url'].split('/status/')[-1]
        
        # Fallback to creating a hash if the URL is not available
        unique_string = f"{tweet_data.get('username', '')}_{tweet_data.get('text', '')}_{tweet_data.get('timestamp', '')}"
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    def _load_master_tweets(self):
        """
        Loads the master tweet dictionary from the JSON file.
        """
        try:
            if os.path.exists(self.master_file):
                with open(self.master_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"[{self.agent_id}] Loaded {len(data)} tweets from master file.")
                    return data
            else:
                print(f"[{self.agent_id}] Master file not found. A new one will be created.")
                return {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"[{self.agent_id}] Error loading master file: {e}. Starting fresh.")
            return {}

    def _save_master_tweets(self):
        """
        Saves the master tweet dictionary to a JSON file with a backup system.
        """
        backup_file = f"{self.master_file}.backup"
        try:
            # Create a backup of the existing file
            if os.path.exists(self.master_file):
                os.rename(self.master_file, backup_file)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.master_file), exist_ok=True)

            # Write the new master file
            with open(self.master_file, 'w', encoding='utf-8') as f:
                json.dump(self.master_tweets, f, indent=2, ensure_ascii=False)
            
            # Remove the backup if the save was successful
            if os.path.exists(backup_file):
                os.remove(backup_file)
        except Exception as e:
            print(f"[{self.agent_id}] Error saving master file: {e}. Restoring from backup.")
            # Restore the backup if something went wrong
            if os.path.exists(backup_file):
                os.rename(backup_file, self.master_file)

    def _save_cookies(self):
        """Saves the current session cookies to the defined session file path."""
        try:
            # MODIFIED: Uses the self.session_file path
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.driver.get_cookies(), f)
            print(f"[{self.agent_id}] Session cookies saved to {self.session_file}")
        except Exception as e:
            print(f"[{self.agent_id}] Error saving cookies: {e}")

    def _load_cookies(self):
        """Loads session cookies from the defined session file path."""
        # MODIFIED: Uses the self.session_file path
        if not os.path.exists(self.session_file):
            return False
        try:
            # MODIFIED: Uses the self.session_file path
            with open(self.session_file, 'rb') as f:
                cookies = pickle.load(f)
            self.driver.get("https://x.com")
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            print(f"[{self.agent_id}] Session cookies loaded from {self.session_file}")
            return True
        except Exception as e:
            print(f"[{self.agent_id}] Error loading cookies: {e}")
            return False

    def _verify_login_status(self):
        """Verifies if the driver's session is currently logged in."""
        try:
            # FIX: Uses self.driver
            self.driver.get("https://x.com/home")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Home timeline']"))
            )
            print(f"[{self.agent_id}] Session is valid.")
            return True
        except TimeoutException:
            print(f"[{self.agent_id}] Session is invalid or expired.")
            return False


    def _export_master_tweets_to_csv(self):
        """Exports the entire master tweet list to a timestamped CSV file."""
        if not self.master_tweets:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Ensure the directory exists
        output_dir = os.path.join("app", "data", "exports")
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, f"marikina_tweets_export_{timestamp}.csv")
        
        try:
            tweets_list = list(self.master_tweets.values())
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=tweets_list[0].keys())
                writer.writeheader()
                writer.writerows(tweets_list)
            print(f"[{self.agent_id}] Exported {len(tweets_list)} tweets to {csv_filename}")
        except Exception as e:
            print(f"[{self.agent_id}] Error exporting to CSV: {e}")