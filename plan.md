## Current Project Structure Analysis

Your project currently has:
- **Basic FastAPI backend** with placeholder agents
- **BaseAgent** class providing common structure
- **FloodAgent** as an example implementation
- **RoutingAgent** integrated into main.py
- **DynamicGraphEnvironment** referenced but imported from graph_manager

## Recommended Project Structure for MAS-FRO

Based on your thesis architecture (Figure 8), here's how you should organize your components:

```
masfro-backend/
├── app/
│   ├── main.py                          # FastAPI entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py                # ✓ Already exists
│   │   ├── flood_agent.py               # Official environmental data
│   │   ├── scout_agent.py               # Crowdsourced VGI data
│   │   ├── hazard_agent.py              # Data fusion & risk assessment
│   │   ├── routing_agent.py             # ✓ Partially exists - A* pathfinding
│   │   ├── evacuation_manager_agent.py  # User interface & feedback loop
│   │   └── communication_viz_agent.py   # Backend for visualization
│   ├── environment/
│   │   ├── __init__.py
│   │   ├── graph_manager.py             # Dynamic Graph Environment (NetworkX)
│   │   └── risk_calculator.py           # Risk scoring functions
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── risk_aware_astar.py          # Modified A* with risk cost function
│   │   └── path_optimizer.py            # Additional optimization logic
│   ├── ml_models/
│   │   ├── __init__.py
│   │   ├── flood_predictor.py           # Random Forest for flood prediction
│   │   └── nlp_processor.py             # NLP for social media text processing
│   ├── data/
│   │   ├── osm/                         # OSM road network data
│   │   ├── flood_hazard/                # DPWH/DOST-NOAH flood maps
│   │   ├── evacuation_centers/          # Shelter locations
│   │   └── simulated/                   # Generated simulation data
│   ├── communication/
│   │   ├── __init__.py
│   │   ├── acl_protocol.py              # Agent Communication Language
│   │   └── message_queue.py             # Inter-agent messaging
│   └── utils/
│       ├── __init__.py
│       ├── geo_utils.py                 # Geospatial helper functions
│       └── validators.py                # Data validation utilities
```

## Key Implementation Priorities

### 1. **Complete the Core Agents** (Phase 5.3 & 5.4 from your Gantt Chart)

**Flood Agent** (`flood_agent.py`):
```python
class FloodAgent(BaseAgent):
    """Collects official environmental data (PAGASA rain gauges, river levels)"""
    def __init__(self, agent_id, environment):
        super().__init__(agent_id, environment)
        self.pagasa_api_url = "..."
        self.river_sensor_url = "..."
    
    def step(self):
        # Scrape/fetch official flood data
        rainfall_data = self.fetch_rainfall_data()
        river_levels = self.fetch_river_levels()
        # Send to Hazard Agent for processing
        self.send_to_hazard_agent(rainfall_data, river_levels)
```

**Scout Agent** (`scout_agent.py`):
```python
class ScoutAgent(BaseAgent):
    """Collects crowdsourced VGI data from social media and navigation apps"""
    def __init__(self, agent_id, environment):
        super().__init__(agent_id, environment)
        self.twitter_api = "..."
        self.waze_api = "..."
    
    def step(self):
        # Collect crowdsourced reports
        social_media_reports = self.scrape_social_media()
        navigation_reports = self.fetch_navigation_data()
        # Process with NLP for textual reports
        processed_reports = self.apply_nlp(social_media_reports)
        # Send to Hazard Agent
        self.send_to_hazard_agent(processed_reports)
```

**Hazard Agent** (`hazard_agent.py`):
```python
class HazardAgent(BaseAgent):
    """Central data fusion & risk assessment hub"""
    def __init__(self, agent_id, environment: DynamicGraphEnvironment):
        super().__init__(agent_id, environment)
        self.flood_predictor = FloodPredictor()  # ML model
        
    def step(self):
        # Receive data from Flood Agent and Scout Agent
        # Validate and fuse data
        fused_data = self.fuse_data()
        # Calculate risk scores for road segments
        risk_scores = self.calculate_risk_scores(fused_data)
        # Update Dynamic Graph Environment
        self.environment.update_edge_weights(risk_scores)
```

**Evacuation Manager Agent** (`evacuation_manager_agent.py`):
```python
class EvacuationManagerAgent(BaseAgent):
    """Manages user requests and feedback loop"""
    def __init__(self, agent_id, environment):
        super().__init__(agent_id, environment)
        self.routing_agent = None  # Reference to RoutingAgent
        
    def handle_route_request(self, start, end):
        # Request route from Routing Agent
        route = self.routing_agent.find_safest_route(start, end)
        return route
    
    def collect_user_feedback(self, route_id, feedback):
        # User reports: "road clear" or "road blocked"
        # Forward to Hazard Agent to update graph
        self.forward_to_hazard_agent(feedback)
```

### 2. **Implement Dynamic Graph Environment** (Phase 5.2)

Your `graph_manager.py` should handle:
- **OSMnx integration** to load Marikina City road network
- **NetworkX graph** with dynamic edge weights
- **Risk score updates** from Hazard Agent

```python
class DynamicGraphEnvironment:
    def __init__(self):
        self.graph = self.load_marikina_network()
        self.risk_scores = {}
        
    def load_marikina_network(self):
        # Use OSMnx to download road network
        import osmnx as ox
        place_name = "Marikina City, Metro Manila, Philippines"
        G = ox.graph_from_place(place_name, network_type='drive')
        return G
    
    def update_edge_weights(self, risk_scores):
        # Update edge weights based on risk + distance
        for edge, risk in risk_scores.items():
            if self.graph.has_edge(*edge):
                self.graph[edge[0]][edge[1]][0]['risk'] = risk
                self.graph[edge[0]][edge[1]][0]['weight'] = (
                    risk * RISK_WEIGHT + 
                    self.graph[edge[0]][edge[1]][0]['length'] * DISTANCE_WEIGHT
                )
```

### 3. **Implement Risk-Aware A*** (Phase 5.3)

```python
# algorithms/risk_aware_astar.py
def risk_aware_astar(graph, start, end):
    """
    Modified A* where:
    - g(n) = cumulative risk scores (not just distance)
    - h(n) = Euclidean/Haversine distance heuristic
    """
    # Use NetworkX's astar_path with custom weight function
    path = nx.astar_path(
        graph, 
        start, 
        end,
        heuristic=haversine_heuristic,
        weight='weight'  # Uses the combined risk+distance weight
    )
    return path
```

### 4. **Agent Communication Protocol** (Phase 5.6)

Implement ACL-based messaging:
```python
# communication/acl_protocol.py
class ACLMessage:
    def __init__(self, performative, sender, receiver, content):
        self.performative = performative  # REQUEST, INFORM, QUERY
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.language = "json"
        self.ontology = "routing"
```

### 5. **ML Integration** (Phase 5.5)

**Flood Predictor** (Random Forest):
```python
# ml_models/flood_predictor.py
from sklearn.ensemble import RandomForestClassifier

class FloodPredictor:
    def __init__(self):
        self.model = RandomForestClassifier()
        self.train_model()
    
    def predict_flood_risk(self, rainfall, river_level, elevation):
        features = [[rainfall, river_level, elevation]]
        return self.model.predict_proba(features)[0][1]
```

**NLP Processor** for social media:
```python
# ml_models/nlp_processor.py
def extract_flood_info(text):
    """Extract flood-related info from Filipino/English text"""
    # Use regex or simple NLP to detect:
    # - Location mentions (e.g., "baha sa Nangka")
    # - Severity indicators
    # - Road status
    pass
```

## Integration with FastAPI (main.py)

Update your `main.py` to initialize all agents:

```python
# Initialize environment
environment = DynamicGraphEnvironment()

# Initialize all agents
flood_agent = FloodAgent("flood_001", environment)
scout_agent = ScoutAgent("scout_001", environment)
hazard_agent = HazardAgent("hazard_001", environment)
routing_agent = RoutingAgent("routing_001", environment)
evac_manager = EvacuationManagerAgent("evac_manager_001", environment)

# Start agent background processes using multiprocessing
# (as per your thesis: Python multiprocessing for true concurrency)
```

## Next Steps (Based on Your Gantt Chart)

You're currently in **Phase 5** (Prototype Development). Focus on:

1. **Week 1-2**: Complete core agent implementations (Flood, Scout, Hazard)
2. **Week 3**: Integrate OSMnx and build Dynamic Graph Environment
3. **Week 4**: Implement risk-aware A* algorithm
4. **Week 5**: Add ML models (Random Forest, NLP)
5. **Week 6**: System integration and unit testing

This structure aligns with your hybrid architecture (hierarchical + decentralized) and ensures each agent operates autonomously while communicating through defined protocols.