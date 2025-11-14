# MAS-FRO Learning Roadmap & Rewrite Checklist

**Purpose:** A structured guide for learning and rewriting the Multi-Agent System for Flood Route Optimization (MAS-FRO) from scratch.

**Estimated Time:** 80-120 hours for complete rewrite
**Skill Level Required:** Intermediate Python, Basic React/Next.js
**Learning Approach:** Bottom-up (foundations → advanced features)

---

## 📚 Prerequisites Checklist

### Knowledge Requirements
- [ ] Python 3.10+ basics (classes, async/await, type hints)
- [ ] FastAPI fundamentals (routes, dependencies, WebSockets)
- [ ] Graph theory basics (nodes, edges, pathfinding)
- [ ] Basic SQL/database concepts
- [ ] React fundamentals (hooks, components, state)
- [ ] REST API and WebSocket concepts

### Tools & Environment Setup
- [ ] Install Python 3.12.3
- [ ] Install UV package manager (`pip install uv`)
- [ ] Install Node.js 18+ and npm
- [ ] Install PostgreSQL 14+
- [ ] Install Git
- [ ] Set up code editor (VS Code recommended)
- [ ] Create GitHub repository for your rewrite

### External Accounts
- [ ] OpenWeatherMap API key (free tier: https://openweathermap.org/api)
- [ ] Mapbox access token (free tier: https://mapbox.com)
- [ ] Twitter/X account (for ScoutAgent scraping - optional)
- [ ] PAGASA website access (https://monitoring.pagasa.dost.gov.ph)

---

## 🎯 Learning Modules

Each module builds on the previous ones. Complete them in order for best results.

---

## Module 1: Project Setup & Foundation (4-6 hours)

### 1.1 Backend Project Initialization
- [ ] Create `masfro-backend/` directory
- [ ] Initialize UV project: `uv init`
- [ ] Create `pyproject.toml` with basic dependencies
  ```toml
  [project]
  name = "masfro-backend"
  version = "0.1.0"
  requires-python = ">=3.10"
  dependencies = ["fastapi>=0.118.0", "uvicorn>=0.37.0"]
  ```
- [ ] Create directory structure:
  ```
  app/
  ├── __init__.py
  ├── main.py
  ├── agents/
  ├── algorithms/
  ├── communication/
  ├── environment/
  ├── services/
  ├── database/
  └── core/
  ```
- [ ] Create `.env` and `.env.example` files
- [ ] Create `.gitignore` for Python projects

**Learning Goal:** Understand UV package management and project structure

**Test:** Run `uv run uvicorn app.main:app --reload` successfully

**Documentation to Create:**
- [ ] `docs/01_PROJECT_SETUP.md` - Setup instructions
- [ ] `docs/ARCHITECTURE_OVERVIEW.md` - High-level system design

---

### 1.2 Frontend Project Initialization
- [ ] Create `masfro-frontend/` directory
- [ ] Initialize Next.js 15: `npx create-next-app@latest`
- [ ] Install dependencies: `npm install mapbox-gl geotiff proj4`
- [ ] Configure `next.config.js` for CORS and API proxy
- [ ] Create directory structure:
  ```
  src/
  ├── app/
  │   ├── page.js
  │   └── layout.js
  ├── components/
  ├── hooks/
  └── utils/
  ```

**Learning Goal:** Understand Next.js 15 App Router structure

**Test:** Run `npm run dev` and see default Next.js page

**Documentation to Create:**
- [ ] `docs/02_FRONTEND_SETUP.md` - Frontend architecture

---

## Module 2: Graph Environment & OSMnx (8-10 hours)

### 2.1 Understand Graph Theory Basics
- [ ] Read about directed vs undirected graphs
- [ ] Understand nodes (intersections) and edges (road segments)
- [ ] Learn about edge weights (distance, risk, time)
- [ ] Study NetworkX library basics

**Learning Resources:**
- NetworkX Tutorial: https://networkx.org/documentation/stable/tutorial.html
- OSMnx Documentation: https://osmnx.readthedocs.io/

---

### 2.2 Graph Manager Implementation
- [ ] Study OSMnx API for downloading road networks
- [ ] Create `app/environment/graph_manager.py`
- [ ] Implement `DynamicGraphEnvironment` class:
  ```python
  class DynamicGraphEnvironment:
      def __init__(self, place_name: str):
          """Load road network from OSMnx or file"""
          pass

      def get_graph(self) -> nx.MultiDiGraph:
          """Return the NetworkX graph"""
          pass

      def update_edge_risk(self, u: int, v: int, risk: float):
          """Update risk score for a road segment"""
          pass

      def get_edge_data(self, u: int, v: int) -> dict:
          """Get attributes of a road segment"""
          pass
  ```
- [ ] Download Marikina City graph: `ox.graph_from_place("Marikina City, Philippines")`
- [ ] Save graph to file: `ox.save_graphml(G, "marikina_graph.graphml")`
- [ ] Implement lazy loading from saved file
- [ ] Add edge attributes: `length`, `risk_score`, `flood_depth`

**Learning Goal:** Understand how to represent road networks as graphs

**Test Cases:**
- [ ] Load graph from file
- [ ] Count nodes and edges (should be ~2,500 nodes, ~5,000 edges)
- [ ] Update edge risk scores
- [ ] Query edge attributes

**Documentation to Create:**
- [ ] `docs/03_GRAPH_ENVIRONMENT.md` - Graph structure explained
- [ ] `docs/OSMnx_GUIDE.md` - How to use OSMnx for road networks

---

### 2.3 Risk Calculator
- [ ] Study flood risk modeling equations
- [ ] Create `app/environment/risk_calculator.py`
- [ ] Implement risk calculation functions:
  ```python
  def calculate_composite_risk(
      flood_depth: float,
      water_velocity: float,
      rainfall_intensity: float
  ) -> float:
      """Calculate risk score 0.0-1.0"""
      pass

  def calculate_hydrological_risk(depth: float, velocity: float) -> float:
      """HR = depth * (velocity + 0.5)"""
      pass

  def calculate_flood_severity(depth: float) -> str:
      """Return: safe, low, moderate, high, extreme"""
      pass
  ```
- [ ] Implement weighted fusion formula:
  ```python
  Risk = α₁ * official_data + α₂ * weather_data + α₃ * crowdsourced_data
  where α₁=0.5, α₂=0.3, α₃=0.2
  ```

**Learning Goal:** Understand how to quantify flood risk mathematically

**Test Cases:**
- [ ] Test risk calculation with known inputs
- [ ] Verify risk scores are always 0.0-1.0
- [ ] Test severity classification thresholds

**Documentation to Create:**
- [ ] `docs/04_RISK_CALCULATION.md` - Mathematical formulas explained
- [ ] `docs/RISK_THRESHOLDS.md` - Severity level definitions

---

## Module 3: Agent Communication Protocol (6-8 hours)

### 3.1 Understand FIPA-ACL Standard
- [ ] Read about FIPA Agent Communication Language
- [ ] Learn about message performatives (INFORM, REQUEST, PROPOSE, etc.)
- [ ] Understand agent-to-agent communication patterns

**Learning Resource:**
- FIPA ACL Spec: http://www.fipa.org/specs/fipa00037/

---

### 3.2 ACL Protocol Implementation
- [ ] Create `app/communication/acl_protocol.py`
- [ ] Implement `Performative` enum:
  ```python
  class Performative(str, Enum):
      INFORM = "inform"
      REQUEST = "request"
      PROPOSE = "propose"
      CONFIRM = "confirm"
      QUERY = "query"
  ```
- [ ] Create `ACLMessage` dataclass:
  ```python
  @dataclass
  class ACLMessage:
      performative: Performative
      sender: str
      receiver: str
      content: Dict[str, Any]
      conversation_id: str
      reply_to: Optional[str] = None
      timestamp: datetime = field(default_factory=datetime.now)
  ```
- [ ] Add helper functions:
  ```python
  def create_inform_message(sender: str, receiver: str, content: dict) -> ACLMessage
  def create_request_message(sender: str, receiver: str, content: dict) -> ACLMessage
  def serialize_message(msg: ACLMessage) -> str
  def deserialize_message(json_str: str) -> ACLMessage
  ```

**Learning Goal:** Understand structured agent communication

**Test Cases:**
- [ ] Create and serialize messages
- [ ] Deserialize JSON back to ACLMessage
- [ ] Validate message structure

**Documentation to Create:**
- [ ] `docs/05_ACL_PROTOCOL.md` - Communication protocol guide
- [ ] `docs/MESSAGE_EXAMPLES.md` - Sample messages for each performative

---

### 3.3 Message Queue System
- [ ] Create `app/communication/message_queue.py`
- [ ] Implement `MessageQueue` class:
  ```python
  class MessageQueue:
      def __init__(self):
          self.queues: Dict[str, asyncio.Queue] = {}

      async def send_message(self, message: ACLMessage):
          """Send message to recipient's queue"""
          pass

      async def receive_message(self, agent_id: str) -> ACLMessage:
          """Receive message from agent's queue"""
          pass

      async def broadcast_message(self, message: ACLMessage, recipients: List[str]):
          """Send message to multiple agents"""
          pass
  ```
- [ ] Add queue management methods (create, delete, clear)

**Learning Goal:** Understand asynchronous message passing

**Test Cases:**
- [ ] Send and receive messages
- [ ] Test broadcast functionality
- [ ] Handle queue overflow scenarios

**Documentation to Create:**
- [ ] `docs/06_MESSAGE_QUEUE.md` - Queue architecture

---

## Module 4: Base Agent & Agent Lifecycle (6-8 hours)

### 4.1 Agent Design Patterns
- [ ] Study the agent paradigm (autonomy, reactivity, proactivity)
- [ ] Understand agent lifecycle (init → run → stop)
- [ ] Learn about agent behaviors and decision-making

---

### 4.2 Base Agent Implementation
- [ ] Create `app/agents/base_agent.py`
- [ ] Implement `BaseAgent` abstract class:
  ```python
  from abc import ABC, abstractmethod

  class BaseAgent(ABC):
      def __init__(self, agent_id: str, message_queue: MessageQueue):
          self.agent_id = agent_id
          self.message_queue = message_queue
          self.is_running = False
          self.logger = logging.getLogger(agent_id)

      @abstractmethod
      async def process_message(self, message: ACLMessage):
          """Process incoming messages"""
          pass

      @abstractmethod
      async def run(self):
          """Main agent loop"""
          pass

      async def send_message(self, receiver: str, performative: Performative, content: dict):
          """Helper to send messages"""
          msg = ACLMessage(
              performative=performative,
              sender=self.agent_id,
              receiver=receiver,
              content=content
          )
          await self.message_queue.send_message(msg)

      def stop(self):
          """Stop agent execution"""
          self.is_running = False
  ```

**Learning Goal:** Understand object-oriented agent design

**Test Cases:**
- [ ] Create mock agent extending BaseAgent
- [ ] Test message sending/receiving
- [ ] Test agent lifecycle (start → run → stop)

**Documentation to Create:**
- [ ] `docs/07_BASE_AGENT.md` - Agent architecture
- [ ] `docs/AGENT_LIFECYCLE.md` - Startup and shutdown procedures

---

## Module 5: FloodAgent - Data Collection (10-12 hours)

### 5.1 Understand Data Sources
- [ ] Study PAGASA website structure (https://monitoring.pagasa.dost.gov.ph)
- [ ] Read OpenWeatherMap API docs (https://openweathermap.org/api)
- [ ] Identify 17 river monitoring stations in Marikina
- [ ] Learn about rainfall intensity classification (light/moderate/heavy/intense)

---

### 5.2 River Scraper Service
- [ ] Install Selenium: `uv add selenium webdriver-manager`
- [ ] Create `app/services/river_scraper_service.py`
- [ ] Implement `RiverScraperService` class:
  ```python
  class RiverScraperService:
      def __init__(self):
          self.driver = None

      def initialize_driver(self):
          """Setup Chrome WebDriver with options"""
          options = webdriver.ChromeOptions()
          options.add_argument('--headless')
          self.driver = webdriver.Chrome(options=options)

      def get_river_levels(self) -> List[Dict[str, Any]]:
          """Scrape PAGASA website for river levels"""
          # Navigate to PAGASA site
          # Extract table data
          # Parse station names, water levels, status
          pass

      def classify_water_level_status(self, level: float, thresholds: dict) -> str:
          """Return: Normal, Alert, Alarm, or Critical"""
          pass
  ```
- [ ] Handle PAGASA website quirks (dynamic content, timeouts)
- [ ] Add retry logic for network failures

**Learning Goal:** Understand web scraping with Selenium

**Test Cases:**
- [ ] Successfully scrape river levels
- [ ] Parse at least 10+ stations
- [ ] Handle connection errors gracefully
- [ ] Verify status classification logic

**Documentation to Create:**
- [ ] `docs/08_RIVER_SCRAPER.md` - Scraping guide
- [ ] `docs/PAGASA_DATA_FORMAT.md` - Data structure documentation

---

### 5.3 Weather Service
- [ ] Get OpenWeatherMap API key
- [ ] Create `app/services/weather_service.py`
- [ ] Implement `WeatherService` class:
  ```python
  class WeatherService:
      def __init__(self, api_key: str):
          self.api_key = api_key
          self.base_url = "https://api.openweathermap.org/data/2.5"

      async def get_current_weather(self, lat: float, lon: float) -> Dict:
          """Get current weather for coordinates"""
          pass

      async def get_forecast(self, lat: float, lon: float) -> List[Dict]:
          """Get 48-hour forecast"""
          pass

      def calculate_rainfall_intensity(self, rain_1h: float) -> str:
          """
          Light: 0-2.5 mm/h
          Moderate: 2.5-10 mm/h
          Heavy: 10-50 mm/h
          Intense: >50 mm/h
          """
          pass
  ```
- [ ] Use `httpx` for async HTTP requests
- [ ] Add caching to reduce API calls

**Learning Goal:** Integrate external REST APIs

**Test Cases:**
- [ ] Fetch weather for Marikina coordinates (14.65°N, 121.10°E)
- [ ] Parse temperature, humidity, wind speed
- [ ] Calculate rainfall intensity correctly

**Documentation to Create:**
- [ ] `docs/09_WEATHER_SERVICE.md` - API integration guide

---

### 5.4 FloodAgent Implementation
- [ ] Create `app/agents/flood_agent.py`
- [ ] Extend `BaseAgent` class
- [ ] Implement data collection methods:
  ```python
  class FloodAgent(BaseAgent):
      def __init__(self, agent_id: str, message_queue: MessageQueue):
          super().__init__(agent_id, message_queue)
          self.river_scraper = RiverScraperService()
          self.weather_service = WeatherService(api_key=os.getenv("OPENWEATHERMAP_API_KEY"))

      async def fetch_real_river_levels(self) -> List[Dict]:
          """Scrape PAGASA river data"""
          pass

      async def fetch_real_weather_data(self) -> Dict:
          """Fetch weather from OpenWeatherMap"""
          pass

      async def collect_and_forward_data(self):
          """Collect all data and send to HazardAgent"""
          river_data = await self.fetch_real_river_levels()
          weather_data = await self.fetch_real_weather_data()

          # Send INFORM message to HazardAgent
          await self.send_message(
              receiver="hazard_agent",
              performative=Performative.INFORM,
              content={
                  "data_type": "flood_data",
                  "river_levels": river_data,
                  "weather": weather_data,
                  "timestamp": datetime.now().isoformat()
              }
          )

      async def run(self):
          """Main agent loop - collect data every 5 minutes"""
          self.is_running = True
          while self.is_running:
              await self.collect_and_forward_data()
              await asyncio.sleep(300)  # 5 minutes
  ```
- [ ] Add fallback to simulated data if APIs fail
- [ ] Implement graceful error handling

**Learning Goal:** Build autonomous data collection agent

**Test Cases:**
- [ ] Test data collection end-to-end
- [ ] Verify message format sent to HazardAgent
- [ ] Test fallback mechanism
- [ ] Monitor agent loop for 15 minutes

**Documentation to Create:**
- [ ] `docs/10_FLOOD_AGENT.md` - FloodAgent architecture
- [ ] `docs/DATA_COLLECTION_FLOW.md` - Data flow diagram

---

## Module 6: ScoutAgent - Twitter Scraping (10-12 hours)

### 6.1 NLP Basics for Tweet Analysis
- [ ] Study text preprocessing (lowercasing, tokenization)
- [ ] Learn about keyword extraction
- [ ] Understand sentiment analysis basics
- [ ] Research flood-related keywords (baha, flood, tubig, etc.)

---

### 6.2 NLP Processor
- [ ] Install scikit-learn: `uv add scikit-learn`
- [ ] Create `app/ml_models/nlp_processor.py`
- [ ] Implement `NLPProcessor` class:
  ```python
  class NLPProcessor:
      def __init__(self):
          self.flood_keywords = [
              'baha', 'flood', 'flooded', 'tubig', 'submerged',
              'knee-deep', 'waist-deep', 'stranded'
          ]
          self.location_keywords = [
              'marikina', 'marcos highway', 'jp rizal', 'riverbanks',
              'sta lucia', 'concepcion', 'parang', 'nangka'
          ]

      def extract_flood_info(self, text: str) -> Optional[Dict]:
          """Extract flood information from tweet text"""
          text_lower = text.lower()

          # Check if flood-related
          has_flood_keyword = any(kw in text_lower for kw in self.flood_keywords)
          if not has_flood_keyword:
              return None

          # Extract severity
          severity = self._extract_severity(text_lower)

          # Extract location
          location = self._extract_location(text_lower)

          return {
              "severity": severity,
              "location": location,
              "confidence": self._calculate_confidence(text_lower)
          }

      def _extract_severity(self, text: str) -> str:
          """
          Levels: minimal, low, moderate, high, extreme
          Based on depth keywords: ankle, knee, waist, chest, roof
          """
          pass

      def _extract_location(self, text: str) -> Optional[str]:
          """Find location mentions in tweet"""
          pass
  ```

**Learning Goal:** Build basic NLP text extraction

**Test Cases:**
- [ ] Test with sample Filipino flood tweets
- [ ] Verify severity extraction accuracy
- [ ] Test location extraction for Marikina areas

**Documentation to Create:**
- [ ] `docs/11_NLP_PROCESSOR.md` - NLP pipeline explained
- [ ] `docs/TWEET_PATTERNS.md` - Common flood tweet patterns

---

### 6.3 Twitter Scraper
- [ ] Create `app/services/twitter_scraper_service.py` (using Selenium)
- [ ] Implement `TwitterScraperService` class:
  ```python
  class TwitterScraperService:
      def __init__(self, username: str, password: str):
          self.username = username
          self.password = password
          self.driver = None

      def login_to_twitter(self):
          """Automate Twitter login"""
          pass

      def search_tweets(self, query: str, max_tweets: int = 50) -> List[Dict]:
          """
          Search for tweets with query like:
          'baha marikina OR flood marikina -filter:retweets'
          """
          pass

      def extract_tweet_data(self, tweet_element) -> Dict:
          """Extract: text, author, timestamp, location"""
          pass
  ```
- [ ] Handle Twitter's anti-bot measures (random delays, human-like scrolling)
- [ ] Add rate limiting

**Learning Goal:** Advanced web scraping techniques

**Test Cases:**
- [ ] Successfully log in to Twitter
- [ ] Search and extract at least 20 tweets
- [ ] Handle CAPTCHA scenarios (manual intervention)

**Documentation to Create:**
- [ ] `docs/12_TWITTER_SCRAPER.md` - Twitter scraping guide
- [ ] `docs/TWITTER_BEST_PRACTICES.md` - Ethical scraping guidelines

---

### 6.4 ScoutAgent Implementation
- [ ] Create `app/agents/scout_agent.py`
- [ ] Extend `BaseAgent` class
- [ ] Implement tweet collection and processing:
  ```python
  class ScoutAgent(BaseAgent):
      def __init__(self, agent_id: str, message_queue: MessageQueue):
          super().__init__(agent_id, message_queue)
          self.twitter_scraper = TwitterScraperService(
              username=os.getenv("TWITTER_USERNAME"),
              password=os.getenv("TWITTER_PASSWORD")
          )
          self.nlp_processor = NLPProcessor()

      async def scrape_tweets(self) -> List[Dict]:
          """Search for flood-related tweets in Marikina"""
          query = "baha marikina OR flood marikina -filter:retweets"
          tweets = self.twitter_scraper.search_tweets(query, max_tweets=50)
          return tweets

      async def extract_flood_reports(self, tweets: List[Dict]) -> List[Dict]:
          """Process tweets with NLP"""
          reports = []
          for tweet in tweets:
              info = self.nlp_processor.extract_flood_info(tweet['text'])
              if info:
                  reports.append({
                      **tweet,
                      **info
                  })
          return reports

      async def collect_and_forward_data(self):
          """Scrape tweets and send to HazardAgent"""
          tweets = await self.scrape_tweets()
          reports = await self.extract_flood_reports(tweets)

          await self.send_message(
              receiver="hazard_agent",
              performative=Performative.INFORM,
              content={
                  "data_type": "crowdsourced",
                  "reports": reports,
                  "source": "twitter",
                  "timestamp": datetime.now().isoformat()
              }
          )

      async def run(self):
          """Main loop - scrape every 10 minutes"""
          self.is_running = True
          while self.is_running:
              await self.collect_and_forward_data()
              await asyncio.sleep(600)  # 10 minutes
  ```

**Learning Goal:** Build autonomous crowdsourced data agent

**Test Cases:**
- [ ] Test tweet scraping and NLP pipeline
- [ ] Verify data quality (relevant reports only)
- [ ] Test message sending to HazardAgent

**Documentation to Create:**
- [ ] `docs/13_SCOUT_AGENT.md` - ScoutAgent architecture
- [ ] `docs/CROWDSOURCED_DATA.md` - Data validation strategies

---

## Module 7: HazardAgent - Data Fusion (8-10 hours)

### 7.1 Understand Data Fusion Techniques
- [ ] Study weighted averaging methods
- [ ] Learn about confidence scoring
- [ ] Understand spatial data fusion (mapping reports to road segments)

---

### 7.2 HazardAgent Implementation
- [ ] Create `app/agents/hazard_agent.py`
- [ ] Implement central hub logic:
  ```python
  class HazardAgent(BaseAgent):
      def __init__(self, agent_id: str, message_queue: MessageQueue, environment: DynamicGraphEnvironment):
          super().__init__(agent_id, message_queue)
          self.environment = environment
          self.risk_calculator = RiskCalculator()

          # Data storage
          self.official_data = {}
          self.weather_data = {}
          self.crowdsourced_data = []

          # Fusion weights
          self.alpha_1 = 0.5  # Official data
          self.alpha_2 = 0.3  # Weather data
          self.alpha_3 = 0.2  # Crowdsourced data

      async def process_message(self, message: ACLMessage):
          """Receive data from FloodAgent and ScoutAgent"""
          if message.performative == Performative.INFORM:
              data_type = message.content.get("data_type")

              if data_type == "flood_data":
                  self.official_data = message.content.get("river_levels", {})
                  self.weather_data = message.content.get("weather", {})

              elif data_type == "crowdsourced":
                  self.crowdsourced_data = message.content.get("reports", [])

              # Trigger risk calculation
              await self.fuse_and_update()

      async def fuse_data(self) -> Dict[str, float]:
          """Combine data sources with confidence weights"""
          fused_risks = {}

          # For each road segment in graph
          G = self.environment.get_graph()
          for u, v, key in G.edges(keys=True):
              # Calculate risk from each source
              official_risk = self._calculate_official_risk(u, v)
              weather_risk = self._calculate_weather_risk(u, v)
              crowdsourced_risk = self._calculate_crowdsourced_risk(u, v)

              # Weighted fusion
              composite_risk = (
                  self.alpha_1 * official_risk +
                  self.alpha_2 * weather_risk +
                  self.alpha_3 * crowdsourced_risk
              )

              fused_risks[(u, v, key)] = composite_risk

          return fused_risks

      async def calculate_risk_scores(self, fused_risks: Dict) -> Dict:
          """Apply risk calculation formulas"""
          risk_scores = {}

          for edge, risk in fused_risks.items():
              # Use RiskCalculator for hydrological risk
              flood_depth = self._estimate_flood_depth(edge)
              velocity = self._estimate_velocity(edge)

              hydrological_risk = self.risk_calculator.calculate_hydrological_risk(
                  depth=flood_depth,
                  velocity=velocity
              )

              # Combine with fused risk
              final_risk = (risk + hydrological_risk) / 2
              risk_scores[edge] = min(final_risk, 1.0)  # Cap at 1.0

          return risk_scores

      async def update_environment(self, risk_scores: Dict):
          """Update graph edge weights"""
          for (u, v, key), risk in risk_scores.items():
              self.environment.update_edge_risk(u, v, risk)

          self.logger.info(f"Updated {len(risk_scores)} road segments with new risk scores")

      async def fuse_and_update(self):
          """Main data fusion pipeline"""
          fused_risks = await self.fuse_data()
          risk_scores = await self.calculate_risk_scores(fused_risks)
          await self.update_environment(risk_scores)

      async def run(self):
          """Listen for messages continuously"""
          self.is_running = True
          while self.is_running:
              # Process incoming messages
              message = await self.message_queue.receive_message(self.agent_id)
              await self.process_message(message)
  ```

**Learning Goal:** Implement multi-source data fusion

**Test Cases:**
- [ ] Test data reception from FloodAgent and ScoutAgent
- [ ] Verify fusion formula correctness
- [ ] Confirm graph edge weights update
- [ ] Test with conflicting data sources

**Documentation to Create:**
- [ ] `docs/14_HAZARD_AGENT.md` - Data fusion architecture
- [ ] `docs/FUSION_ALGORITHM.md` - Weighted fusion explained
- [ ] `docs/RISK_SCORING.md` - Complete scoring methodology

---

## Module 8: Risk-Aware A* Algorithm (8-10 hours)

### 8.1 Understand A* Pathfinding
- [ ] Study basic A* algorithm (g(n) + h(n))
- [ ] Learn about heuristic functions (Euclidean, Manhattan, Haversine)
- [ ] Understand open set and closed set
- [ ] Study priority queues (heapq in Python)

**Learning Resource:**
- A* Pathfinding: https://www.redblobgames.com/pathfinding/a-star/introduction.html

---

### 8.2 Risk-Aware A* Implementation
- [ ] Create `app/algorithms/risk_aware_astar.py`
- [ ] Implement modified A* with risk weighting:
  ```python
  import heapq
  from typing import List, Tuple, Optional
  import networkx as nx

  def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
      """
      Calculate great-circle distance between two points on Earth.
      Returns distance in meters.
      """
      from math import radians, sin, cos, sqrt, atan2

      R = 6371000  # Earth radius in meters

      phi1 = radians(lat1)
      phi2 = radians(lat2)
      delta_phi = radians(lat2 - lat1)
      delta_lambda = radians(lon2 - lon1)

      a = sin(delta_phi/2)**2 + cos(phi1) * cos(phi2) * sin(delta_lambda/2)**2
      c = 2 * atan2(sqrt(a), sqrt(1-a))

      return R * c

  def risk_aware_astar(
      graph: nx.MultiDiGraph,
      start_node: int,
      goal_node: int,
      weight_risk: float = 0.6,
      weight_distance: float = 0.4,
      max_risk_threshold: float = 0.9
  ) -> Optional[List[int]]:
      """
      Modified A* that balances safety and distance.

      Args:
          graph: Road network graph
          start_node: Starting intersection
          goal_node: Destination intersection
          weight_risk: Weight for risk component (default 0.6)
          weight_distance: Weight for distance component (default 0.4)
          max_risk_threshold: Maximum acceptable risk (default 0.9)

      Returns:
          List of node IDs forming the path, or None if no safe path exists
      """
      # Priority queue: (f_score, node)
      open_set = [(0, start_node)]

      # Track visited nodes
      closed_set = set()

      # Store best path to each node
      came_from = {}

      # g_score: cost from start to node
      g_score = {start_node: 0}

      # f_score: g_score + heuristic
      f_score = {start_node: _heuristic(graph, start_node, goal_node)}

      while open_set:
          # Get node with lowest f_score
          current_f, current = heapq.heappop(open_set)

          # Found goal
          if current == goal_node:
              return _reconstruct_path(came_from, current)

          if current in closed_set:
              continue

          closed_set.add(current)

          # Explore neighbors
          for neighbor in graph.neighbors(current):
              if neighbor in closed_set:
                  continue

              # Get edge data
              edge_data = graph.get_edge_data(current, neighbor, 0)

              # Check risk threshold
              risk = edge_data.get('risk_score', 0.0)
              if risk > max_risk_threshold:
                  continue  # Skip dangerous roads

              # Calculate composite cost
              distance = edge_data.get('length', 0)
              composite_cost = (
                  weight_risk * risk +
                  weight_distance * (distance / 1000)  # Normalize distance
              )

              tentative_g_score = g_score[current] + composite_cost

              # Found better path to neighbor
              if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                  came_from[neighbor] = current
                  g_score[neighbor] = tentative_g_score

                  h = _heuristic(graph, neighbor, goal_node)
                  f_score[neighbor] = tentative_g_score + h

                  heapq.heappush(open_set, (f_score[neighbor], neighbor))

      # No path found
      return None

  def _heuristic(graph: nx.MultiDiGraph, node: int, goal: int) -> float:
      """
      Haversine heuristic for A*.
      Admissible: never overestimates actual cost.
      """
      node_data = graph.nodes[node]
      goal_data = graph.nodes[goal]

      distance = haversine_distance(
          node_data['y'], node_data['x'],
          goal_data['y'], goal_data['x']
      )

      # Return normalized distance (assume minimum risk of 0)
      return distance / 1000

  def _reconstruct_path(came_from: dict, current: int) -> List[int]:
      """Rebuild path from goal to start"""
      path = [current]
      while current in came_from:
          current = came_from[current]
          path.append(current)
      return list(reversed(path))

  def calculate_path_metrics(graph: nx.MultiDiGraph, path: List[int]) -> dict:
      """
      Calculate total distance, average risk, and estimated time.
      """
      total_distance = 0
      total_risk = 0
      num_edges = 0

      for i in range(len(path) - 1):
          edge_data = graph.get_edge_data(path[i], path[i+1], 0)
          total_distance += edge_data.get('length', 0)
          total_risk += edge_data.get('risk_score', 0)
          num_edges += 1

      avg_risk = total_risk / num_edges if num_edges > 0 else 0

      # Estimate time (assume 30 km/h average speed)
      avg_speed_kmh = 30
      estimated_time_minutes = (total_distance / 1000) / (avg_speed_kmh / 60)

      return {
          "total_distance_meters": total_distance,
          "total_distance_km": round(total_distance / 1000, 2),
          "average_risk": round(avg_risk, 3),
          "estimated_time_minutes": round(estimated_time_minutes, 1),
          "num_segments": num_edges
      }
  ```

**Learning Goal:** Implement advanced pathfinding with custom cost function

**Test Cases:**
- [ ] Test A* with known start/end nodes
- [ ] Verify path avoids high-risk edges
- [ ] Compare risk-aware path vs shortest path
- [ ] Test with various weight combinations
- [ ] Test edge case: no safe path exists

**Documentation to Create:**
- [ ] `docs/15_RISK_AWARE_ASTAR.md` - Algorithm explained
- [ ] `docs/ASTAR_TUNING.md` - Parameter tuning guide
- [ ] `docs/PATHFINDING_COMPARISON.md` - A* vs Dijkstra vs BFS

---

## Module 9: RoutingAgent (6-8 hours)

### 9.1 Evacuation Centers
- [ ] Research 15 official evacuation centers in Marikina
- [ ] Create `app/data/evacuation_centers.json`:
  ```json
  [
    {
      "id": "ec_001",
      "name": "Marikina Sports Center",
      "latitude": 14.6507,
      "longitude": 121.1029,
      "capacity": 5000,
      "facilities": ["medical", "food", "water", "electricity"]
    },
    ...
  ]
  ```

---

### 9.2 RoutingAgent Implementation
- [ ] Create `app/agents/routing_agent.py`
- [ ] Implement route calculation logic:
  ```python
  class RoutingAgent(BaseAgent):
      def __init__(self, agent_id: str, message_queue: MessageQueue, environment: DynamicGraphEnvironment):
          super().__init__(agent_id, message_queue)
          self.environment = environment
          self.evacuation_centers = self._load_evacuation_centers()

      def _load_evacuation_centers(self) -> List[Dict]:
          """Load evacuation centers from JSON file"""
          pass

      async def calculate_route(
          self,
          start_lat: float,
          start_lon: float,
          end_lat: float,
          end_lon: float
      ) -> Optional[Dict]:
          """
          Calculate risk-aware route between two points.
          """
          G = self.environment.get_graph()

          # Find nearest nodes
          start_node = ox.distance.nearest_nodes(G, start_lon, start_lat)
          end_node = ox.distance.nearest_nodes(G, end_lon, end_lat)

          # Run A* algorithm
          path = risk_aware_astar(
              graph=G,
              start_node=start_node,
              goal_node=end_node,
              weight_risk=0.6,
              weight_distance=0.4,
              max_risk_threshold=0.9
          )

          if path is None:
              return None

          # Calculate metrics
          metrics = calculate_path_metrics(G, path)

          # Convert path to coordinates
          route_coords = [
              {"lat": G.nodes[node]['y'], "lon": G.nodes[node]['x']}
              for node in path
          ]

          return {
              "path_nodes": path,
              "route_coordinates": route_coords,
              "metrics": metrics
          }

      async def find_nearest_evacuation_center(
          self,
          lat: float,
          lon: float,
          top_n: int = 3
      ) -> List[Dict]:
          """
          Find N nearest evacuation centers with safe routes.
          """
          results = []

          for center in self.evacuation_centers:
              route = await self.calculate_route(
                  start_lat=lat,
                  start_lon=lon,
                  end_lat=center['latitude'],
                  end_lon=center['longitude']
              )

              if route:
                  results.append({
                      "center": center,
                      "route": route
                  })

          # Sort by safety (lowest risk) then distance
          results.sort(key=lambda x: (
              x['route']['metrics']['average_risk'],
              x['route']['metrics']['total_distance_meters']
          ))

          return results[:top_n]

      async def process_message(self, message: ACLMessage):
          """Handle route requests from EvacuationManagerAgent"""
          if message.performative == Performative.REQUEST:
              action = message.content.get('action')

              if action == 'calculate_route':
                  route = await self.calculate_route(
                      start_lat=message.content['start_lat'],
                      start_lon=message.content['start_lon'],
                      end_lat=message.content['end_lat'],
                      end_lon=message.content['end_lon']
                  )

                  # Send response
                  await self.send_message(
                      receiver=message.sender,
                      performative=Performative.INFORM,
                      content={
                          'action': 'route_result',
                          'route': route
                      }
                  )

      async def run(self):
          """Listen for route requests"""
          self.is_running = True
          while self.is_running:
              message = await self.message_queue.receive_message(self.agent_id)
              await self.process_message(message)
  ```

**Learning Goal:** Build pathfinding agent with practical features

**Test Cases:**
- [ ] Test route calculation between two coordinates
- [ ] Verify nearest evacuation center finding
- [ ] Test with coordinates outside Marikina (should fail gracefully)
- [ ] Compare routes with different risk thresholds

**Documentation to Create:**
- [ ] `docs/16_ROUTING_AGENT.md` - RoutingAgent architecture
- [ ] `docs/EVACUATION_CENTERS.md` - Center locations and facilities

---

## Module 10: EvacuationManagerAgent (6-8 hours)

### 10.1 EvacuationManagerAgent Implementation
- [ ] Create `app/agents/evacuation_manager_agent.py`
- [ ] Implement user interface agent:
  ```python
  class EvacuationManagerAgent(BaseAgent):
      def __init__(self, agent_id: str, message_queue: MessageQueue):
          super().__init__(agent_id, message_queue)
          self.pending_requests = {}  # Track user requests
          self.feedback_data = []

      async def handle_route_request(
          self,
          request_id: str,
          start_lat: float,
          start_lon: float,
          destination_type: str,  # "evacuation_center" or "custom"
          end_lat: Optional[float] = None,
          end_lon: Optional[float] = None
      ) -> str:
          """
          Handle route request from user (via WebSocket).
          Returns conversation_id for tracking.
          """
          # Request route from RoutingAgent
          conversation_id = f"conv_{request_id}"

          await self.send_message(
              receiver="routing_agent",
              performative=Performative.REQUEST,
              content={
                  "action": "calculate_route" if destination_type == "custom" else "find_evacuation_center",
                  "start_lat": start_lat,
                  "start_lon": start_lon,
                  "end_lat": end_lat,
                  "end_lon": end_lon,
                  "conversation_id": conversation_id
              }
          )

          self.pending_requests[conversation_id] = {
              "request_id": request_id,
              "timestamp": datetime.now(),
              "status": "pending"
          }

          return conversation_id

      async def process_message(self, message: ACLMessage):
          """Handle responses from RoutingAgent"""
          if message.performative == Performative.INFORM:
              conv_id = message.content.get('conversation_id')

              if conv_id in self.pending_requests:
                  # Extract route data
                  route = message.content.get('route')

                  # Update request status
                  self.pending_requests[conv_id]['status'] = 'completed'
                  self.pending_requests[conv_id]['route'] = route

                  # Notify frontend via WebSocket (handled in FastAPI main.py)
                  return route

      async def collect_user_feedback(
          self,
          request_id: str,
          feedback_type: str,  # "route_taken", "route_blocked", "flood_depth"
          feedback_data: dict
      ):
          """
          Collect feedback from users about routes and conditions.
          This helps improve future recommendations.
          """
          self.feedback_data.append({
              "request_id": request_id,
              "feedback_type": feedback_type,
              "data": feedback_data,
              "timestamp": datetime.now().isoformat()
          })

          # Forward to HazardAgent for data fusion
          if feedback_type == "flood_depth":
              await self.send_message(
                  receiver="hazard_agent",
                  performative=Performative.INFORM,
                  content={
                      "data_type": "user_feedback",
                      "feedback": feedback_data
                  }
              )

      async def run(self):
          """Listen for messages"""
          self.is_running = True
          while self.is_running:
              message = await self.message_queue.receive_message(self.agent_id)
              await self.process_message(message)
  ```

**Learning Goal:** Build user-facing agent with feedback loop

**Test Cases:**
- [ ] Test route request handling
- [ ] Verify conversation tracking
- [ ] Test feedback collection
- [ ] Test integration with RoutingAgent

**Documentation to Create:**
- [ ] `docs/17_EVACUATION_MANAGER.md` - User interaction patterns
- [ ] `docs/FEEDBACK_SYSTEM.md` - Feedback collection strategy

---

## Module 11: FastAPI Backend Integration (10-12 hours)

### 11.1 Basic FastAPI Setup
- [ ] Create `app/main.py`
- [ ] Set up FastAPI application with CORS:
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware

  app = FastAPI(
      title="MAS-FRO API",
      description="Multi-Agent System for Flood Route Optimization",
      version="1.0.0"
  )

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"]
  )
  ```

---

### 11.2 Agent Initialization
- [ ] Create startup event to initialize all agents:
  ```python
  from contextlib import asynccontextmanager

  # Global agent instances
  graph_env = None
  message_queue = None
  agents = {}

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      """Startup and shutdown events"""
      global graph_env, message_queue, agents

      # Startup
      logger.info("Starting MAS-FRO system...")

      # Initialize graph environment
      graph_env = DynamicGraphEnvironment(place_name="Marikina City, Philippines")

      # Initialize message queue
      message_queue = MessageQueue()

      # Initialize agents
      agents['flood'] = FloodAgent("flood_agent", message_queue)
      agents['scout'] = ScoutAgent("scout_agent", message_queue)
      agents['hazard'] = HazardAgent("hazard_agent", message_queue, graph_env)
      agents['routing'] = RoutingAgent("routing_agent", message_queue, graph_env)
      agents['evacuation'] = EvacuationManagerAgent("evacuation_manager", message_queue)

      # Start agents in background tasks
      for agent_name, agent in agents.items():
          asyncio.create_task(agent.run())
          logger.info(f"Started {agent_name}")

      logger.info("All agents running successfully")

      yield

      # Shutdown
      logger.info("Shutting down agents...")
      for agent in agents.values():
          agent.stop()

  app = FastAPI(lifespan=lifespan)
  ```

---

### 11.3 REST API Endpoints
- [ ] Implement route request endpoint:
  ```python
  from pydantic import BaseModel

  class RouteRequest(BaseModel):
      start_lat: float
      start_lon: float
      destination_type: str  # "evacuation_center" or "custom"
      end_lat: Optional[float] = None
      end_lon: Optional[float] = None

  @app.post("/api/route/request")
  async def request_route(request: RouteRequest):
      """Request flood-safe route"""
      request_id = str(uuid.uuid4())

      conversation_id = await agents['evacuation'].handle_route_request(
          request_id=request_id,
          start_lat=request.start_lat,
          start_lon=request.start_lon,
          destination_type=request.destination_type,
          end_lat=request.end_lat,
          end_lon=request.end_lon
      )

      # Wait for response (with timeout)
      route = await _wait_for_route(conversation_id, timeout=10)

      return {
          "request_id": request_id,
          "route": route,
          "timestamp": datetime.now().isoformat()
      }
  ```

- [ ] Implement system status endpoint:
  ```python
  @app.get("/api/system/status")
  async def get_system_status():
      """Get status of all agents"""
      return {
          "agents": {
              name: {
                  "running": agent.is_running,
                  "agent_id": agent.agent_id
              }
              for name, agent in agents.items()
          },
          "graph": {
              "nodes": graph_env.get_graph().number_of_nodes(),
              "edges": graph_env.get_graph().number_of_edges()
          },
          "timestamp": datetime.now().isoformat()
      }
  ```

- [ ] Implement evacuation centers endpoint:
  ```python
  @app.get("/api/evacuation-centers")
  async def get_evacuation_centers():
      """List all evacuation centers"""
      return agents['routing'].evacuation_centers
  ```

- [ ] Implement flood data endpoint:
  ```python
  @app.get("/api/flood-data/current")
  async def get_current_flood_data():
      """Get latest flood data from FloodAgent"""
      return {
          "river_levels": agents['flood'].latest_river_data,
          "weather": agents['flood'].latest_weather_data,
          "timestamp": datetime.now().isoformat()
      }
  ```

**Learning Goal:** Build RESTful API for multi-agent system

**Test Cases:**
- [ ] Test each endpoint with curl or Postman
- [ ] Verify agent initialization on startup
- [ ] Test error handling for invalid requests

**Documentation to Create:**
- [ ] `docs/18_API_ENDPOINTS.md` - Complete API reference
- [ ] `docs/API_EXAMPLES.md` - Request/response examples

---

### 11.4 WebSocket for Real-time Updates
- [ ] Implement WebSocket connection manager:
  ```python
  from fastapi import WebSocket, WebSocketDisconnect
  from typing import Set

  class ConnectionManager:
      def __init__(self):
          self.active_connections: Set[WebSocket] = set()

      async def connect(self, websocket: WebSocket):
          await websocket.accept()
          self.active_connections.add(websocket)

      def disconnect(self, websocket: WebSocket):
          self.active_connections.remove(websocket)

      async def broadcast(self, message: dict):
          """Send message to all connected clients"""
          for connection in self.active_connections:
              try:
                  await connection.send_json(message)
              except:
                  # Connection closed, will be removed on disconnect
                  pass

  manager = ConnectionManager()

  @app.websocket("/ws")
  async def websocket_endpoint(websocket: WebSocket):
      await manager.connect(websocket)

      try:
          while True:
              # Receive messages from client
              data = await websocket.receive_json()

              # Handle different message types
              if data.get('type') == 'route_request':
                  # Process route request
                  pass

              elif data.get('type') == 'feedback':
                  # Collect feedback
                  await agents['evacuation'].collect_user_feedback(
                      request_id=data['request_id'],
                      feedback_type=data['feedback_type'],
                      feedback_data=data['data']
                  )

      except WebSocketDisconnect:
          manager.disconnect(websocket)
  ```

- [ ] Implement flood data broadcasting:
  ```python
  async def broadcast_flood_update():
      """Background task to broadcast flood updates every 5 minutes"""
      while True:
          await asyncio.sleep(300)  # 5 minutes

          flood_data = {
              "type": "flood_update",
              "data": {
                  "river_levels": agents['flood'].latest_river_data,
                  "weather": agents['flood'].latest_weather_data,
                  "timestamp": datetime.now().isoformat()
              }
          }

          await manager.broadcast(flood_data)

  # Start in lifespan
  asyncio.create_task(broadcast_flood_update())
  ```

**Learning Goal:** Implement real-time WebSocket communication

**Test Cases:**
- [ ] Connect multiple WebSocket clients
- [ ] Verify broadcast to all clients
- [ ] Test reconnection after disconnect

**Documentation to Create:**
- [ ] `docs/19_WEBSOCKET_PROTOCOL.md` - WebSocket message formats
- [ ] `docs/REALTIME_UPDATES.md` - Broadcasting strategy

---

## Module 12: Database Integration (8-10 hours)

### 12.1 PostgreSQL Setup
- [ ] Install PostgreSQL 14+
- [ ] Create database: `CREATE DATABASE masfro_db;`
- [ ] Create user: `CREATE USER masfro_user WITH PASSWORD 'password';`
- [ ] Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE masfro_db TO masfro_user;`

---

### 12.2 SQLAlchemy Models
- [ ] Install dependencies: `uv add sqlalchemy psycopg2-binary alembic`
- [ ] Create `app/database/models.py`:
  ```python
  from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
  from sqlalchemy.orm import relationship, declarative_base
  from sqlalchemy.dialects.postgresql import UUID
  import uuid
  from datetime import datetime

  Base = declarative_base()

  class FloodDataCollection(Base):
      __tablename__ = "flood_data_collections"

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      collected_at = Column(DateTime, default=datetime.now, nullable=False)

      # Relationships
      river_levels = relationship("RiverLevel", back_populates="collection", cascade="all, delete-orphan")
      weather_data = relationship("WeatherData", back_populates="collection", cascade="all, delete-orphan")

  class RiverLevel(Base):
      __tablename__ = "river_levels"

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      collection_id = Column(UUID(as_uuid=True), ForeignKey("flood_data_collections.id"))

      station_name = Column(String(100), nullable=False)
      water_level = Column(Float, nullable=False)
      status = Column(String(20))  # Normal, Alert, Alarm, Critical

      collection = relationship("FloodDataCollection", back_populates="river_levels")

  class WeatherData(Base):
      __tablename__ = "weather_data"

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      collection_id = Column(UUID(as_uuid=True), ForeignKey("flood_data_collections.id"))

      temperature = Column(Float)
      humidity = Column(Float)
      wind_speed = Column(Float)
      rainfall_intensity = Column(String(20))

      collection = relationship("FloodDataCollection", back_populates="weather_data")
  ```

---

### 12.3 Database Connection
- [ ] Create `app/database/connection.py`:
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  import os

  DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://masfro_user:password@localhost:5432/masfro_db")

  engine = create_engine(DATABASE_URL, pool_pre_ping=True)
  SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

  def get_db():
      """Dependency for FastAPI routes"""
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```

---

### 12.4 Alembic Migrations
- [ ] Initialize Alembic: `uv run alembic init alembic`
- [ ] Configure `alembic.ini` with database URL
- [ ] Create initial migration: `uv run alembic revision --autogenerate -m "Initial schema"`
- [ ] Run migration: `uv run alembic upgrade head`

---

### 12.5 Repository Pattern
- [ ] Create `app/database/repositories.py`:
  ```python
  from sqlalchemy.orm import Session
  from typing import List, Optional
  from datetime import datetime, timedelta

  class FloodDataRepository:
      def __init__(self, db: Session):
          self.db = db

      def save_collection(
          self,
          river_levels: List[dict],
          weather_data: dict
      ) -> FloodDataCollection:
          """Save flood data collection to database"""
          collection = FloodDataCollection()

          # Add river levels
          for river in river_levels:
              collection.river_levels.append(RiverLevel(**river))

          # Add weather data
          collection.weather_data.append(WeatherData(**weather_data))

          self.db.add(collection)
          self.db.commit()
          self.db.refresh(collection)

          return collection

      def get_latest_collection(self) -> Optional[FloodDataCollection]:
          """Get most recent data collection"""
          return self.db.query(FloodDataCollection)\
              .order_by(FloodDataCollection.collected_at.desc())\
              .first()

      def get_history(
          self,
          start_date: datetime,
          end_date: datetime
      ) -> List[FloodDataCollection]:
          """Get collections within date range"""
          return self.db.query(FloodDataCollection)\
              .filter(FloodDataCollection.collected_at.between(start_date, end_date))\
              .all()
  ```

---

### 12.6 Integrate with FloodAgent
- [ ] Modify FloodAgent to save data to database:
  ```python
  async def collect_and_forward_data(self):
      """Collect data and save to database"""
      river_data = await self.fetch_real_river_levels()
      weather_data = await self.fetch_real_weather_data()

      # Save to database
      db = next(get_db())
      repo = FloodDataRepository(db)
      collection = repo.save_collection(river_data, weather_data)

      # Forward to HazardAgent
      await self.send_message(...)
  ```

**Learning Goal:** Implement database persistence layer

**Test Cases:**
- [ ] Test database connection
- [ ] Save and retrieve flood data
- [ ] Query historical data
- [ ] Test relationships (collections → river_levels → weather_data)

**Documentation to Create:**
- [ ] `docs/20_DATABASE_SCHEMA.md` - Schema design
- [ ] `docs/DATABASE_QUERIES.md` - Common query patterns

---

## Module 13: Automated Scheduler (6-8 hours)

### 13.1 Scheduler Service
- [ ] Create `app/services/flood_data_scheduler.py`:
  ```python
  import asyncio
  from datetime import datetime

  class FloodDataScheduler:
      def __init__(self, interval_minutes: int = 5):
          self.interval_minutes = interval_minutes
          self.is_running = False
          self.stats = {
              "total_runs": 0,
              "successful_runs": 0,
              "failed_runs": 0,
              "last_run": None
          }

      async def collect_data(self):
          """Trigger data collection from FloodAgent"""
          try:
              # This will be called by the scheduler
              await agents['flood'].collect_and_forward_data()

              self.stats['successful_runs'] += 1
              self.stats['last_run'] = datetime.now().isoformat()

          except Exception as e:
              self.stats['failed_runs'] += 1
              logger.error(f"Scheduler error: {e}")

          finally:
              self.stats['total_runs'] += 1

      async def start(self):
          """Start scheduler loop"""
          self.is_running = True

          while self.is_running:
              await self.collect_data()
              await asyncio.sleep(self.interval_minutes * 60)

      def stop(self):
          """Stop scheduler"""
          self.is_running = False

      def get_stats(self) -> dict:
          """Get scheduler statistics"""
          return self.stats

  # Global scheduler instance
  scheduler = None

  def get_scheduler() -> FloodDataScheduler:
      return scheduler
  ```

---

### 13.2 Integrate with FastAPI
- [ ] Start scheduler in lifespan event:
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      global scheduler

      # ... agent initialization ...

      # Start scheduler
      scheduler = FloodDataScheduler(interval_minutes=5)
      asyncio.create_task(scheduler.start())
      logger.info("Scheduler started (5-minute intervals)")

      yield

      # Shutdown
      scheduler.stop()
  ```

- [ ] Add scheduler endpoints:
  ```python
  @app.get("/api/scheduler/status")
  async def get_scheduler_status():
      """Get scheduler status"""
      return {
          "running": scheduler.is_running,
          "interval_minutes": scheduler.interval_minutes,
          "stats": scheduler.get_stats()
      }

  @app.post("/api/scheduler/trigger")
  async def trigger_collection():
      """Manually trigger data collection"""
      await scheduler.collect_data()
      return {"message": "Data collection triggered"}
  ```

**Learning Goal:** Implement automated background tasks

**Test Cases:**
- [ ] Verify scheduler runs every 5 minutes
- [ ] Test manual trigger endpoint
- [ ] Monitor stats accumulation

**Documentation to Create:**
- [ ] `docs/21_SCHEDULER.md` - Scheduler architecture
- [ ] `docs/AUTOMATION.md` - Automated workflows

---

## Module 14: GeoTIFF Integration (8-10 hours)

### 14.1 Understand GeoTIFF Format
- [ ] Study GeoTIFF structure (raster data, bands, geo-referencing)
- [ ] Learn about coordinate reference systems (CRS)
- [ ] Understand EPSG:4326 (WGS84) and EPSG:3857 (Web Mercator)

---

### 14.2 GeoTIFF Service
- [ ] Install Rasterio: `uv add rasterio pyproj`
- [ ] Create `app/services/geotiff_service.py`:
  ```python
  import rasterio
  from rasterio.transform import xy
  from pyproj import Transformer
  from functools import lru_cache
  from typing import Optional, Tuple

  class GeoTIFFService:
      def __init__(self, data_dir: str = "app/data/timed_floodmaps"):
          self.data_dir = data_dir
          self.loaded_maps = {}  # Cache loaded maps
          self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

      @lru_cache(maxsize=72)
      def load_flood_map(self, return_period: str, time_step: int) -> Optional[rasterio.DatasetReader]:
          """
          Load GeoTIFF file with LRU caching.

          Args:
              return_period: "rr01" (2-year), "rr02" (5-year), "rr03", "rr04" (10-year)
              time_step: 1-18 (hours)

          Returns:
              Rasterio dataset reader
          """
          filename = f"{return_period}_step_{time_step:02d}.tif"
          filepath = os.path.join(self.data_dir, return_period, filename)

          if not os.path.exists(filepath):
              return None

          return rasterio.open(filepath)

      def get_flood_depth_at_point(
          self,
          lat: float,
          lon: float,
          return_period: str,
          time_step: int
      ) -> Optional[float]:
          """
          Query flood depth at specific coordinates.

          Returns:
              Flood depth in meters, or None if outside bounds
          """
          dataset = self.load_flood_map(return_period, time_step)
          if dataset is None:
              return None

          # Transform coordinates to dataset CRS
          x, y = self.transformer.transform(lon, lat)

          # Get row/col in raster
          row, col = dataset.index(x, y)

          # Check bounds
          if row < 0 or row >= dataset.height or col < 0 or col >= dataset.width:
              return None

          # Read value
          depth = dataset.read(1)[row, col]

          # Filter nodata values
          if depth == dataset.nodata or depth < 0:
              return None

          return float(depth)

      def get_available_maps(self) -> List[dict]:
          """List all available GeoTIFF files"""
          maps = []

          for rp in ["rr01", "rr02", "rr03", "rr04"]:
              for step in range(1, 19):
                  filepath = os.path.join(self.data_dir, rp, f"{rp}_step_{step:02d}.tif")
                  if os.path.exists(filepath):
                      maps.append({
                          "return_period": rp,
                          "time_step": step,
                          "filename": f"{rp}_step_{step:02d}.tif"
                      })

          return maps
  ```

---

### 14.3 GeoTIFF API Endpoints
- [ ] Add GeoTIFF endpoints to FastAPI:
  ```python
  from fastapi.staticfiles import StaticFiles

  geotiff_service = GeoTIFFService()

  # Serve TIFF files statically
  app.mount("/data/timed_floodmaps", StaticFiles(directory="app/data/timed_floodmaps"), name="floodmaps")

  @app.get("/api/geotiff/available-maps")
  async def get_available_maps():
      """List all 72 flood maps"""
      return geotiff_service.get_available_maps()

  @app.get("/api/geotiff/flood-depth")
  async def get_flood_depth(
      lat: float,
      lon: float,
      return_period: str,
      time_step: int
  ):
      """Query flood depth at specific coordinates"""
      depth = geotiff_service.get_flood_depth_at_point(lat, lon, return_period, time_step)

      if depth is None:
          raise HTTPException(status_code=404, detail="No flood data at coordinates")

      return {
          "latitude": lat,
          "longitude": lon,
          "return_period": return_period,
          "time_step": time_step,
          "flood_depth_meters": depth
      }
  ```

---

### 14.4 Integrate GeoTIFF with HazardAgent
- [ ] Modify HazardAgent to query GeoTIFF data:
  ```python
  class HazardAgent(BaseAgent):
      def __init__(self, ...):
          # ... existing code ...
          self.geotiff_service = GeoTIFFService()

      def _calculate_official_risk(self, u: int, v: int) -> float:
          """Calculate risk using GeoTIFF flood depth"""
          G = self.environment.get_graph()
          edge_data = G.get_edge_data(u, v, 0)

          # Get edge midpoint coordinates
          lat = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
          lon = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2

          # Query GeoTIFF for flood depth (use current return period and time step)
          depth = self.geotiff_service.get_flood_depth_at_point(
              lat, lon,
              return_period="rr02",  # 5-year flood
              time_step=1  # Current hour
          )

          if depth is None or depth < 0.01:
              return 0.0

          # Convert depth to risk score (0.0-1.0)
          # Safe: <0.2m, Low: 0.2-0.5m, Moderate: 0.5-1.0m, High: 1.0-2.0m, Extreme: >2.0m
          if depth < 0.2:
              return 0.1
          elif depth < 0.5:
              return 0.3
          elif depth < 1.0:
              return 0.5
          elif depth < 2.0:
              return 0.7
          else:
              return 0.9
  ```

**Learning Goal:** Integrate geospatial data with routing system

**Test Cases:**
- [ ] Load and query GeoTIFF files
- [ ] Verify coordinate transformation
- [ ] Test flood depth extraction for known coordinates
- [ ] Integrate with HazardAgent risk calculation

**Documentation to Create:**
- [ ] `docs/22_GEOTIFF_INTEGRATION.md` - GeoTIFF architecture
- [ ] `docs/COORDINATE_SYSTEMS.md` - CRS explanation
- [ ] `docs/FLOOD_MAP_DATA.md` - GeoTIFF file organization

---

## Module 15: Frontend - Next.js Setup (8-10 hours)

### 15.1 Project Initialization
- [ ] Create Next.js project (already done in Module 1.2)
- [ ] Configure `next.config.js`:
  ```javascript
  /** @type {import('next').NextConfig} */
  const nextConfig = {
    async rewrites() {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*'
        }
      ]
    }
  }

  module.exports = nextConfig
  ```

---

### 15.2 WebSocket Hook
- [ ] Create `src/hooks/useWebSocket.js`:
  ```javascript
  import { useEffect, useState, useRef } from 'react';

  export default function useWebSocket(url) {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const ws = useRef(null);

    useEffect(() => {
      const connect = () => {
        ws.current = new WebSocket(url);

        ws.current.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
        };

        ws.current.onmessage = (event) => {
          const message = JSON.parse(event.data);
          setLastMessage(message);
        };

        ws.current.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);

          // Auto-reconnect after 5 seconds
          setTimeout(() => {
            connect();
          }, 5000);
        };

        ws.current.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
      };

      connect();

      return () => {
        if (ws.current) {
          ws.current.close();
        }
      };
    }, [url]);

    const sendMessage = (message) => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify(message));
      }
    };

    return { isConnected, lastMessage, sendMessage };
  }
  ```

---

### 15.3 Mapbox Map Component
- [ ] Create `src/components/MapboxMap.js`:
  ```javascript
  'use client';

  import { useEffect, useRef, useState } from 'react';
  import mapboxgl from 'mapbox-gl';
  import 'mapbox-gl/dist/mapbox-gl.css';

  mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

  export default function MapboxMap({ route, floodData }) {
    const mapContainer = useRef(null);
    const map = useRef(null);
    const [lng] = useState(121.1029); // Marikina City center
    const [lat] = useState(14.6507);
    const [zoom] = useState(13);

    useEffect(() => {
      if (map.current) return; // Initialize map only once

      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [lng, lat],
        zoom: zoom
      });

      // Add navigation controls
      map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

      // Add Marikina City boundary
      map.current.on('load', () => {
        // Load boundary GeoJSON
        map.current.addSource('marikina-boundary', {
          type: 'geojson',
          data: '/data/marikina_boundary.geojson'
        });

        map.current.addLayer({
          id: 'marikina-boundary-line',
          type: 'line',
          source: 'marikina-boundary',
          paint: {
            'line-color': '#FF6B35',
            'line-width': 3
          }
        });
      });
    }, []);

    // Update route when it changes
    useEffect(() => {
      if (!map.current || !route) return;

      // Remove existing route
      if (map.current.getLayer('route')) {
        map.current.removeLayer('route');
        map.current.removeSource('route');
      }

      // Add new route
      map.current.addSource('route', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: route.route_coordinates.map(coord => [coord.lon, coord.lat])
          }
        }
      });

      map.current.addLayer({
        id: 'route',
        type: 'line',
        source: 'route',
        paint: {
          'line-color': '#2ECC71',
          'line-width': 5,
          'line-opacity': 0.8
        }
      });

      // Fit map to route bounds
      const bounds = new mapboxgl.LngLatBounds();
      route.route_coordinates.forEach(coord => {
        bounds.extend([coord.lon, coord.lat]);
      });
      map.current.fitBounds(bounds, { padding: 50 });

    }, [route]);

    return (
      <div className="relative w-full h-full">
        <div ref={mapContainer} className="w-full h-full" />
      </div>
    );
  }
  ```

---

### 15.4 Main Dashboard Page
- [ ] Create `src/app/page.js`:
  ```javascript
  'use client';

  import { useState } from 'react';
  import MapboxMap from '@/components/MapboxMap';
  import useWebSocket from '@/hooks/useWebSocket';

  export default function Home() {
    const [startLat, setStartLat] = useState('');
    const [startLon, setStartLon] = useState('');
    const [route, setRoute] = useState(null);
    const [loading, setLoading] = useState(false);

    const { isConnected, lastMessage } = useWebSocket('ws://localhost:8000/ws');

    const handleRouteRequest = async () => {
      setLoading(true);

      try {
        const response = await fetch('http://localhost:8000/api/route/request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            start_lat: parseFloat(startLat),
            start_lon: parseFloat(startLon),
            destination_type: 'evacuation_center'
          })
        });

        const data = await response.json();
        setRoute(data.route);
      } catch (error) {
        console.error('Route request failed:', error);
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="flex h-screen">
        {/* Sidebar */}
        <div className="w-96 bg-white p-6 shadow-lg overflow-y-auto">
          <h1 className="text-2xl font-bold mb-6">MAS-FRO</h1>
          <p className="text-sm text-gray-600 mb-4">
            Multi-Agent System for Flood Route Optimization
          </p>

          {/* Connection Status */}
          <div className="mb-6">
            <span className={`inline-block px-3 py-1 rounded text-sm ${
              isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Route Request Form */}
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium mb-1">Start Latitude</label>
              <input
                type="number"
                step="0.000001"
                value={startLat}
                onChange={(e) => setStartLat(e.target.value)}
                placeholder="14.6507"
                className="w-full px-3 py-2 border rounded"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Start Longitude</label>
              <input
                type="number"
                step="0.000001"
                value={startLon}
                onChange={(e) => setStartLon(e.target.value)}
                placeholder="121.1029"
                className="w-full px-3 py-2 border rounded"
              />
            </div>

            <button
              onClick={handleRouteRequest}
              disabled={loading || !startLat || !startLon}
              className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-300"
            >
              {loading ? 'Finding Route...' : 'Find Safe Route'}
            </button>
          </div>

          {/* Route Metrics */}
          {route && (
            <div className="bg-gray-50 p-4 rounded space-y-2">
              <h3 className="font-semibold">Route Metrics</h3>
              <p className="text-sm">
                Distance: <span className="font-medium">{route.metrics.total_distance_km} km</span>
              </p>
              <p className="text-sm">
                Risk Score: <span className={`font-medium ${
                  route.metrics.average_risk < 0.3 ? 'text-green-600' :
                  route.metrics.average_risk < 0.6 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {(route.metrics.average_risk * 100).toFixed(1)}%
                </span>
              </p>
              <p className="text-sm">
                Est. Time: <span className="font-medium">{route.metrics.estimated_time_minutes} min</span>
              </p>
            </div>
          )}
        </div>

        {/* Map */}
        <div className="flex-1">
          <MapboxMap route={route} />
        </div>
      </div>
    );
  }
  ```

**Learning Goal:** Build interactive React UI with real-time updates

**Test Cases:**
- [ ] Test map rendering
- [ ] Test WebSocket connection
- [ ] Submit route request and display result
- [ ] Test reconnection after disconnect

**Documentation to Create:**
- [ ] `docs/23_FRONTEND_ARCHITECTURE.md` - Frontend overview
- [ ] `docs/MAPBOX_INTEGRATION.md` - Mapbox setup guide
- [ ] `docs/UI_COMPONENTS.md` - Component documentation

---

## Module 16: GeoTIFF Visualization (6-8 hours)

### 16.1 GeoTIFF Rendering on Map
- [ ] Modify MapboxMap.js to render GeoTIFF overlay:
  ```javascript
  import { fromArrayBuffer } from 'geotiff';

  // Inside MapboxMap component
  const [returnPeriod, setReturnPeriod] = useState('rr02');
  const [timeStep, setTimeStep] = useState(1);

  useEffect(() => {
    if (!map.current) return;

    const loadGeoTIFF = async () => {
      const url = `http://localhost:8000/data/timed_floodmaps/${returnPeriod}/${returnPeriod}_step_${timeStep.toString().padStart(2, '0')}.tif`;

      const response = await fetch(url);
      const arrayBuffer = await response.arrayBuffer();
      const tiff = await fromArrayBuffer(arrayBuffer);
      const image = await tiff.getImage();
      const data = await image.readRasters();

      // Convert to canvas
      const canvas = document.createElement('canvas');
      canvas.width = image.getWidth();
      canvas.height = image.getHeight();
      const ctx = canvas.getContext('2d');
      const imageData = ctx.createImageData(canvas.width, canvas.height);

      // Apply color gradient based on flood depth
      for (let i = 0; i < data[0].length; i++) {
        const depth = data[0][i];
        const pixelIndex = i * 4;

        if (depth > 0.01) {
          // Gradient: cyan → blue → navy
          if (depth < 0.5) {
            imageData.data[pixelIndex] = 0;
            imageData.data[pixelIndex + 1] = 255;
            imageData.data[pixelIndex + 2] = 255;
            imageData.data[pixelIndex + 3] = 150;
          } else if (depth < 1.0) {
            imageData.data[pixelIndex] = 0;
            imageData.data[pixelIndex + 1] = 0;
            imageData.data[pixelIndex + 2] = 255;
            imageData.data[pixelIndex + 3] = 180;
          } else {
            imageData.data[pixelIndex] = 0;
            imageData.data[pixelIndex + 1] = 0;
            imageData.data[pixelIndex + 2] = 128;
            imageData.data[pixelIndex + 3] = 200;
          }
        }
      }

      ctx.putImageData(imageData, 0, 0);

      // Add canvas as Mapbox layer
      if (map.current.getLayer('flood-overlay')) {
        map.current.removeLayer('flood-overlay');
        map.current.removeSource('flood-overlay');
      }

      map.current.addSource('flood-overlay', {
        type: 'canvas',
        canvas: canvas,
        coordinates: [
          [121.08, 14.75], // top-left
          [121.13, 14.75], // top-right
          [121.13, 14.61], // bottom-right
          [121.08, 14.61]  // bottom-left
        ]
      });

      map.current.addLayer({
        id: 'flood-overlay',
        type: 'raster',
        source: 'flood-overlay',
        paint: {
          'raster-opacity': 0.7
        }
      });
    };

    loadGeoTIFF();
  }, [returnPeriod, timeStep]);

  // Add controls for return period and time step
  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Controls */}
      <div className="absolute top-4 left-4 bg-white p-4 rounded shadow">
        <div className="mb-2">
          <label className="block text-sm font-medium mb-1">Return Period</label>
          <select
            value={returnPeriod}
            onChange={(e) => setReturnPeriod(e.target.value)}
            className="w-full border rounded px-2 py-1"
          >
            <option value="rr01">2-year flood (RR01)</option>
            <option value="rr02">5-year flood (RR02)</option>
            <option value="rr03">Higher flood (RR03)</option>
            <option value="rr04">10-year flood (RR04)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Time Step: {timeStep}h</label>
          <input
            type="range"
            min="1"
            max="18"
            value={timeStep}
            onChange={(e) => setTimeStep(parseInt(e.target.value))}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
  ```

**Learning Goal:** Render geospatial raster data on web maps

**Test Cases:**
- [ ] Load and display GeoTIFF overlay
- [ ] Test color gradient visualization
- [ ] Test return period selector
- [ ] Test time slider (1-18 hours)

**Documentation to Create:**
- [ ] `docs/24_GEOTIFF_VISUALIZATION.md` - Frontend GeoTIFF rendering
- [ ] `docs/COLOR_SCHEMES.md` - Flood depth color mapping

---

## Module 17: Testing & Validation (10-12 hours)

### 17.1 Unit Tests
- [ ] Install pytest: `uv add --dev pytest pytest-asyncio pytest-cov`
- [ ] Create test files for each module:
  ```python
  # tests/test_risk_calculator.py
  import pytest
  from app.environment.risk_calculator import RiskCalculator

  def test_calculate_composite_risk():
      calculator = RiskCalculator()
      risk = calculator.calculate_composite_risk(
          flood_depth=0.5,
          water_velocity=1.0,
          rainfall_intensity=10.0
      )
      assert 0.0 <= risk <= 1.0

  def test_hydrological_risk():
      calculator = RiskCalculator()
      risk = calculator.calculate_hydrological_risk(depth=1.0, velocity=2.0)
      assert risk > 0
  ```

- [ ] Test coverage for:
  - [ ] Risk calculation functions
  - [ ] ACL message serialization
  - [ ] Graph manager operations
  - [ ] A* pathfinding algorithm
  - [ ] Data fusion logic

---

### 17.2 Integration Tests
- [ ] Create integration test suite:
  ```python
  # tests/test_integration.py
  import pytest
  from app.main import app
  from httpx import AsyncClient

  @pytest.mark.asyncio
  async def test_route_request():
      async with AsyncClient(app=app, base_url="http://test") as client:
          response = await client.post("/api/route/request", json={
              "start_lat": 14.6507,
              "start_lon": 121.1029,
              "destination_type": "evacuation_center"
          })
          assert response.status_code == 200
          assert "route" in response.json()
  ```

- [ ] Test scenarios:
  - [ ] End-to-end route request
  - [ ] WebSocket connection
  - [ ] Database persistence
  - [ ] Agent communication

---

### 17.3 System Testing
- [ ] Create test plan document
- [ ] Test with real data sources
- [ ] Stress test with multiple concurrent requests
- [ ] Monitor system performance (CPU, memory)
- [ ] Test failure scenarios (API down, database connection lost)

**Documentation to Create:**
- [ ] `docs/25_TESTING_GUIDE.md` - Complete testing strategy
- [ ] `docs/TEST_SCENARIOS.md` - Test case specifications

---

## Module 18: Documentation & Deployment (8-10 hours)

### 18.1 Complete Documentation
- [ ] Write README.md with setup instructions
- [ ] Document all API endpoints (OpenAPI/Swagger)
- [ ] Create architecture diagrams
- [ ] Write user guide
- [ ] Document configuration options

---

### 18.2 Deployment Preparation
- [ ] Create Docker containers:
  ```dockerfile
  # Backend Dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY . .
  RUN pip install uv && uv sync
  CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [ ] Create docker-compose.yml:
  ```yaml
  version: '3.8'
  services:
    backend:
      build: ./masfro-backend
      ports:
        - "8000:8000"
      environment:
        - DATABASE_URL=postgresql://user:password@db:5432/masfro_db

    frontend:
      build: ./masfro-frontend
      ports:
        - "3000:3000"

    db:
      image: postgres:14
      environment:
        POSTGRES_DB: masfro_db
        POSTGRES_USER: user
        POSTGRES_PASSWORD: password
      volumes:
        - postgres_data:/var/lib/postgresql/data

  volumes:
    postgres_data:
  ```

---

### 18.3 Deployment
- [ ] Deploy to cloud platform (AWS, Google Cloud, Azure)
- [ ] Set up CI/CD pipeline
- [ ] Configure monitoring and logging
- [ ] Set up SSL certificates

**Documentation to Create:**
- [ ] `docs/26_DEPLOYMENT_GUIDE.md` - Deployment instructions
- [ ] `docs/DOCKER_GUIDE.md` - Container setup
- [ ] `docs/PRODUCTION_CHECKLIST.md` - Pre-launch checklist

---

## 📝 Final Checklist

### Code Quality
- [ ] All files under 500 lines
- [ ] All functions under 50 lines
- [ ] Type hints on all functions
- [ ] Google-style docstrings
- [ ] PEP 8 compliance (run `ruff check`)
- [ ] No hardcoded credentials

### Testing
- [ ] 80%+ test coverage
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing completed

### Documentation
- [ ] All 26 module docs created
- [ ] README.md complete
- [ ] API documentation (Swagger)
- [ ] Architecture diagrams
- [ ] User guide

### Deployment
- [ ] Docker containers working
- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] Monitoring set up

---

## 🎓 Learning Outcomes

By completing this roadmap, you will have learned:

1. **Multi-agent systems** - Design and implement autonomous agents
2. **Real-time data collection** - Web scraping, API integration
3. **NLP** - Text extraction and classification
4. **Graph algorithms** - Pathfinding with custom cost functions
5. **Data fusion** - Combining multi-source data with confidence weighting
6. **Geospatial analysis** - Working with GeoTIFF, coordinate systems
7. **FastAPI** - REST APIs, WebSockets, background tasks
8. **Database design** - PostgreSQL, SQLAlchemy, migrations
9. **Next.js** - React, App Router, real-time UI
10. **Mapbox** - Interactive web mapping
11. **Deployment** - Docker, CI/CD, production systems

---

## 📚 Additional Resources

### Books
- "Artificial Intelligence: A Modern Approach" (Russell & Norvig)
- "Web Scraping with Python" (Ryan Mitchell)
- "Graph Algorithms" (Mark Needham)

### Online Courses
- FastAPI Official Tutorial: https://fastapi.tiangolo.com/tutorial/
- NetworkX Documentation: https://networkx.org/documentation/stable/
- Next.js Learn: https://nextjs.org/learn

### Communities
- r/python, r/FastAPI, r/nextjs
- Stack Overflow
- GitHub Discussions

---

## 🤝 Support

If you get stuck:
1. Re-read the module documentation
2. Check test cases for examples
3. Search Stack Overflow
4. Ask in relevant communities
5. Review the original MAS-FRO codebase for reference

---

**Good luck with your learning journey! 🚀**

Remember: Learning by rebuilding is one of the best ways to deeply understand complex systems. Take your time, test thoroughly, and don't skip modules - each builds on the previous ones.
