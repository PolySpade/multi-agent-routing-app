# ScoutAgent Migration to MAS Architecture

**Status:** ✅ **COMPLETE**
**Date:** November 20, 2025

---

## Summary

Refactored `ScoutAgent` to use the MessageQueue pattern with FIPA-ACL protocol, eliminating tight coupling to HazardAgent and completing the MAS architecture migration for all data collection agents (FloodAgent, ScoutAgent).

---

## Problem Statement

### Issue: Tight Coupling and Blocking Calls

**Before MAS Refactoring:**
```python
# ScoutAgent (OLD - WRONG)
class ScoutAgent:
    def __init__(self, agent_id, environment, hazard_agent):
        self.hazard_agent = hazard_agent  # Direct reference!

    def set_hazard_agent(self, hazard_agent):
        self.hazard_agent = hazard_agent  # Tight coupling!

    def _process_and_forward_tweets(self, tweets):
        # ... process tweets ...

        # Direct synchronous method call (blocking!)
        self.hazard_agent.process_scout_data_with_coordinates(processed_reports)
```

**Issues:**
- ScoutAgent has direct reference to HazardAgent
- Synchronous blocking method calls
- Cannot scale to multiple agents
- Violates MAS mailbox pattern
- Bypasses MessageQueue infrastructure

---

## Solution Architecture

### MAS Communication Flow

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│ ScoutAgent   │                    │ MessageQueue │                    │ HazardAgent  │
└──────┬───────┘                    └──────┬───────┘                    └──────┬───────┘
       │                                   │                                   │
       │ 1. collect tweets                 │                                   │
       │ 2. process with NLP               │                                   │
       │ 3. geocode locations              │                                   │
       │                                   │                                   │
       │ 4. create_inform_message()        │                                   │
       │    (scout_report_batch)           │                                   │
       │                                   │                                   │
       │ 5. send_message(ACLMessage)       │                                   │
       │──────────────────────────────────>│                                   │
       │                                   │                                   │
       │                                   │ 6. queue.put(message)             │
       │                                   │───────────────────────────────────>│
       │                                   │                                   │
       │                                   │         7. step() - poll queue    │
       │                                   │<───────────────────────────────────│
       │                                   │                                   │
       │                                   │ 8. receive_message()              │
       │                                   │───────────────────────────────────>│
       │                                   │                                   │
       │                                   │ 9. return ACLMessage              │
       │                                   │<───────────────────────────────────│
       │                                   │                                   │
       │                                   │   10. _handle_inform_message()    │
       │                                   │   11. _handle_scout_report_batch()│
       │                                   │   12. process_scout_data_*()      │
       │                                   │   13. update_graph_edges()        │
```

---

## Implementation Details

### 1. Updated Imports

**File:** `masfro-backend/app/agents/scout_agent.py` (Lines 24-33)

**Changes:**
```python
# ACL Protocol imports for MAS communication
try:
    from communication.acl_protocol import ACLMessage, Performative, create_inform_message
except ImportError:
    from app.communication.acl_protocol import ACLMessage, Performative, create_inform_message

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from ..core.credentials import TwitterCredentials
    from ..communication.message_queue import MessageQueue  # NEW: MAS communication
    # REMOVED: from .hazard_agent import HazardAgent
```

---

### 2. Refactored `__init__` Method

**File:** `masfro-backend/app/agents/scout_agent.py` (Lines 57-111)

**Before:**
```python
def __init__(
    self,
    agent_id: str,
    environment: "DynamicGraphEnvironment",
    credentials: Optional["TwitterCredentials"] = None,
    hazard_agent: Optional["HazardAgent"] = None,  # ❌ Direct reference
    simulation_mode: bool = False,
    simulation_scenario: int = 1,
    use_ml_in_simulation: bool = True
) -> None:
    super().__init__(agent_id, environment)
    self._credentials = credentials
    self.driver = None
    self.hazard_agent = hazard_agent  # ❌ Tight coupling
```

**After:**
```python
def __init__(
    self,
    agent_id: str,
    environment: "DynamicGraphEnvironment",
    message_queue: Optional["MessageQueue"] = None,  # ✅ MAS communication
    credentials: Optional["TwitterCredentials"] = None,
    hazard_agent_id: str = "hazard_agent_001",  # ✅ Target agent ID
    simulation_mode: bool = False,
    simulation_scenario: int = 1,
    use_ml_in_simulation: bool = True
) -> None:
    super().__init__(agent_id, environment)

    # Message queue for MAS communication
    self.message_queue = message_queue
    self.hazard_agent_id = hazard_agent_id

    # Register with message queue
    if self.message_queue:
        try:
            self.message_queue.register_agent(self.agent_id)
            logger.info(f"{self.agent_id} registered with MessageQueue")
        except ValueError as e:
            logger.warning(f"{self.agent_id} already registered: {e}")

    self._credentials = credentials
    self.driver = None
```

---

### 3. Removed `set_hazard_agent` Method

**Deleted:** Lines 166-174

**Reason:** Direct agent linking no longer needed with MessageQueue architecture.

---

### 4. Updated Message Check

**File:** `masfro-backend/app/agents/scout_agent.py` (Lines 248-250)

**Before:**
```python
if not self.hazard_agent:
    logger.warning(f"{self.agent_id} has no HazardAgent reference, data not forwarded")
    return
```

**After:**
```python
if not self.message_queue:
    logger.warning(f"{self.agent_id} has no MessageQueue, data not forwarded")
    return
```

---

### 5. Replaced Direct Call (With Coordinates)

**File:** `masfro-backend/app/agents/scout_agent.py` (Lines 307-346)

**Before:**
```python
# Forward all processed reports to HazardAgent using coordinate-based method
if processed_reports:
    logger.info(
        f"{self.agent_id} forwarding {len(processed_reports)} "
        f"flood reports with coordinates to HazardAgent"
    )
    self.hazard_agent.process_scout_data_with_coordinates(processed_reports)  # ❌ Direct call
```

**After:**
```python
# Forward all processed reports to HazardAgent via MessageQueue (MAS architecture)
if processed_reports:
    logger.info(
        f"{self.agent_id} forwarding {len(processed_reports)} "
        f"flood reports with coordinates to {self.hazard_agent_id} via MessageQueue"
    )

    try:
        # Create ACL INFORM message with scout reports (with coordinates)
        message = create_inform_message(
            sender=self.agent_id,
            receiver=self.hazard_agent_id,
            info_type="scout_report_batch",  # Standard message type
            data={
                "reports": processed_reports,
                "has_coordinates": True,  # Flag for HazardAgent
                "report_count": len(processed_reports),
                "skipped_count": skipped_no_coordinates
            }
        )

        # Send via message queue
        self.message_queue.send_message(message)

        logger.info(
            f"{self.agent_id} successfully sent INFORM message to "
            f"{self.hazard_agent_id} ({len(processed_reports)} reports with coordinates)"
        )

    except Exception as e:
        logger.error(
            f"{self.agent_id} failed to send message to {self.hazard_agent_id}: {e}"
        )
```

---

### 6. Replaced Direct Call (Without Coordinates - Legacy)

**File:** `masfro-backend/app/agents/scout_agent.py` (Lines 392-423)

**Before:**
```python
# Forward using legacy method without coordinates
if processed_reports:
    logger.info(
        f"{self.agent_id} forwarding {len(processed_reports)} "
        f"flood reports to HazardAgent (legacy mode without coordinates)"
    )
    self.hazard_agent.process_scout_data(processed_reports)  # ❌ Direct call
```

**After:**
```python
# Forward via MessageQueue (MAS architecture) - legacy mode without coordinates
if processed_reports:
    logger.info(
        f"{self.agent_id} forwarding {len(processed_reports)} "
        f"flood reports to {self.hazard_agent_id} via MessageQueue (legacy mode without coordinates)"
    )

    try:
        # Create ACL INFORM message with scout reports (without coordinates)
        message = create_inform_message(
            sender=self.agent_id,
            receiver=self.hazard_agent_id,
            info_type="scout_report_batch",  # Standard message type
            data={
                "reports": processed_reports,
                "has_coordinates": False,  # Flag for HazardAgent
                "report_count": len(processed_reports)
            }
        )

        # Send via message queue
        self.message_queue.send_message(message)

        logger.info(
            f"{self.agent_id} successfully sent INFORM message to "
            f"{self.hazard_agent_id} ({len(processed_reports)} reports without coordinates)"
        )

    except Exception as e:
        logger.error(
            f"{self.agent_id} failed to send message to {self.hazard_agent_id}: {e}"
        )
```

---

### 7. Updated HazardAgent Handler

**File:** `masfro-backend/app/agents/hazard_agent.py` (Lines 565-593)

**Before:**
```python
def _handle_scout_report_batch(self, data: List[Dict[str, Any]], sender: str) -> None:
    """Handle scout report batch from ScoutAgent."""
    logger.info(
        f"{self.agent_id} received scout report batch from {sender}: "
        f"{len(data)} reports"
    )

    # Process each scout report
    for report in data:
        self.process_scout_data(report)  # ❌ Only legacy processing
```

**After:**
```python
def _handle_scout_report_batch(self, data: Dict[str, Any], sender: str) -> None:
    """
    Handle scout report batch from ScoutAgent.

    Args:
        data: Dict containing scout reports and metadata:
              - "reports": List of scout reports
              - "has_coordinates": Boolean flag indicating coordinate availability
              - "report_count": Number of reports
              - "skipped_count": Number of reports skipped (optional)
        sender: ID of sending agent
    """
    reports = data.get("reports", [])
    has_coordinates = data.get("has_coordinates", False)
    report_count = data.get("report_count", len(reports))

    logger.info(
        f"{self.agent_id} received scout report batch from {sender}: "
        f"{report_count} reports ({'with' if has_coordinates else 'without'} coordinates)"
    )

    # Use appropriate processing method based on coordinate availability
    if has_coordinates:
        # Process reports with coordinates (spatial filtering enabled)
        self.process_scout_data_with_coordinates(reports)  # ✅ Coordinate-based processing
    else:
        # Process reports without coordinates (legacy method)
        for report in reports:
            self.process_scout_data(report)  # ✅ Legacy processing
```

**Key Changes:**
- ✅ Accepts `Dict` instead of `List` to support metadata
- ✅ Checks `has_coordinates` flag to route to appropriate processing method
- ✅ Supports both coordinate-based and legacy processing paths

---

### 8. Updated main.py

**File:** `masfro-backend/app/main.py` (Lines 437-445)

**Before:**
```python
scout_agent = ScoutAgent(
    "scout_agent_001",
    environment,
    hazard_agent=hazard_agent,  # ❌ Direct reference
    simulation_mode=True,
    simulation_scenario=1,
    use_ml_in_simulation=True
)
```

**After:**
```python
scout_agent = ScoutAgent(
    "scout_agent_001",
    environment,
    message_queue=message_queue,  # ✅ MAS communication
    hazard_agent_id="hazard_agent_001",  # ✅ Target agent for messages
    simulation_mode=True,
    simulation_scenario=1,
    use_ml_in_simulation=True
)
```

---

## Message Structure

### ACL Message Format (With Coordinates)

```python
{
    "performative": "INFORM",
    "sender": "scout_agent_001",
    "receiver": "hazard_agent_001",
    "content": {
        "info_type": "scout_report_batch",
        "data": {
            "reports": [
                {
                    "location": "Sto Nino",
                    "coordinates": {"lat": 14.6341, "lon": 121.1014},  # KEY: Spatial data
                    "severity": 0.75,
                    "report_type": "flood_depth",
                    "confidence": 0.88,
                    "timestamp": "2025-11-20T11:30:00+08:00",
                    "source": "twitter",
                    "source_url": "https://twitter.com/...",
                    "username": "marikina_resident",
                    "text": "Heavy flooding in Sto Nino area, water knee-deep!"
                },
                # ... more reports
            ],
            "has_coordinates": true,  # ✅ Flag for coordinate-based processing
            "report_count": 15,
            "skipped_count": 3
        }
    },
    "language": "json",
    "ontology": "routing",
    "conversation_id": "...",
    "message_id": "..."
}
```

### ACL Message Format (Without Coordinates - Legacy)

```python
{
    "performative": "INFORM",
    "sender": "scout_agent_001",
    "receiver": "hazard_agent_001",
    "content": {
        "info_type": "scout_report_batch",
        "data": {
            "reports": [
                {
                    "location": "Marikina",  # No coordinates - text only
                    "severity": 0.65,
                    "report_type": "flood_depth",
                    "confidence": 0.72,
                    "timestamp": "2025-11-20T11:30:00+08:00",
                    "source": "twitter",
                    "source_url": "https://twitter.com/...",
                    "username": "marikina_user",
                    "text": "Flooding reported in Marikina!"
                },
                # ... more reports
            ],
            "has_coordinates": false,  # ✅ Flag for legacy processing
            "report_count": 8
        }
    },
    "language": "json",
    "ontology": "routing"
}
```

---

## Verification

### Import Test

```bash
cd masfro-backend
uv run python -c "from app.main import app"
```

**Key Log Messages (Success):**
```
✅ Agent scout_agent_001 registered with message queue
✅ scout_agent_001 registered with MessageQueue
✅ ScoutAgent 'scout_agent_001' initialized in SIMULATION MODE
✅ MAS-FRO system initialized successfully
```

---

## Testing the MAS Communication

### Step 1: Start Backend Server

```bash
cd masfro-backend
uv run uvicorn app.main:app --reload
```

### Step 2: Start Simulation

```bash
curl -X POST "http://localhost:8000/api/simulation/start?mode=light"
```

### Step 3: Expected Log Pattern (Each Tick)

**ScoutAgent Step:**
```
INFO - scout_agent_001 performing step (simulation mode)
INFO - scout_agent_001 forwarding 15 flood reports with coordinates to hazard_agent_001 via MessageQueue
INFO - scout_agent_001 successfully sent INFORM message to hazard_agent_001 (15 reports with coordinates)
```

**HazardAgent Step:**
```
DEBUG - hazard_agent_001 performing step at 2025-11-20 12:00:00
INFO - hazard_agent_001 processed 1 messages from queue
INFO - hazard_agent_001 received scout report batch from scout_agent_001: 15 reports (with coordinates)
DEBUG - Spatial query (indexed): Found 342 edges within 800m of (14.6341, 121.1014)
INFO - hazard_agent_001 updated 1234 edges with risk scores
```

---

## Benefits of MAS Refactoring

### Before (Tight Coupling)

| Aspect | Status |
|--------|--------|
| **Coupling** | ❌ Direct agent references |
| **Communication** | ❌ Synchronous blocking calls |
| **Scalability** | ❌ Cannot add new agents easily |
| **Protocol** | ❌ No standardized messages |
| **Performance** | ❌ Blocking calls slow system |
| **Testing** | ❌ Hard to mock dependencies |

### After (MAS Architecture)

| Aspect | Status |
|--------|--------|
| **Coupling** | ✅ Decoupled via MessageQueue |
| **Communication** | ✅ Asynchronous non-blocking |
| **Scalability** | ✅ Easy to add new agents |
| **Protocol** | ✅ FIPA-ACL standard |
| **Performance** | ✅ Non-blocking, efficient |
| **Testing** | ✅ Easy to mock MessageQueue |

---

## Complete MAS Agent Matrix

| Agent | MAS Refactored | MessageQueue | ACL Messages | Status |
|-------|----------------|--------------|--------------|--------|
| **FloodAgent** | ✅ | ✅ | ✅ INFORM (flood_data_batch) | Complete |
| **HazardAgent** | ✅ | ✅ | ✅ Receives & processes | Complete |
| **ScoutAgent** | ✅ | ✅ | ✅ INFORM (scout_report_batch) | Complete |
| **RoutingAgent** | ⚠️ | ❌ | ❌ | Not yet migrated |
| **EvacuationManager** | ⚠️ | ❌ | ❌ | Not yet migrated |

**Progress:** 3/5 agents (60%) using MAS architecture

---

## Future Enhancements

### 1. Twitter API v2 Migration

Replace Selenium-based scraping with official Twitter API v2:

```python
# Future implementation
class ScoutAgent:
    def __init__(self, api_client: tweepy.Client, ...):
        self.twitter_client = api_client

    async def collect_tweets_api_v2(self):
        """Collect tweets using Twitter API v2 (Stream API)."""
        tweets = await self.twitter_client.search_recent_tweets(
            query="flood Marikina",
            max_results=100,
            tweet_fields=["created_at", "geo"],
            expansions=["geo.place_id"]
        )
        return self._process_api_tweets(tweets)
```

**Benefits:**
- ✅ More reliable than web scraping
- ✅ Official rate limits and quotas
- ✅ Better geo-location data
- ✅ Real-time streaming support

### 2. Multi-Channel Social Media

Expand beyond Twitter to other platforms:

```python
# Future: Multi-channel scout agent
class MultiChannelScoutAgent(ScoutAgent):
    def __init__(self, ...):
        self.twitter_client = TwitterClient()
        self.facebook_client = FacebookClient()
        self.instagram_client = InstagramClient()

    async def collect_social_media_data(self):
        """Collect from multiple social media platforms."""
        twitter_data = await self.collect_twitter()
        facebook_data = await self.collect_facebook()
        instagram_data = await self.collect_instagram()

        # Merge and deduplicate
        return self._merge_reports([twitter_data, facebook_data, instagram_data])
```

### 3. Sentiment Analysis

Add sentiment analysis to gauge urgency:

```python
# Future: Sentiment-based urgency scoring
def calculate_urgency(self, report: Dict) -> float:
    """Calculate urgency score based on sentiment analysis."""
    sentiment = self.sentiment_analyzer.analyze(report['text'])

    urgency = 0.0
    if sentiment['panic_level'] > 0.7:
        urgency += 0.3
    if sentiment['help_request']:
        urgency += 0.2
    if report['severity'] > 0.8:
        urgency += 0.5

    return min(urgency, 1.0)
```

---

## Related Documentation

- **MAS Architecture:** `MAS_REFACTORING_COMPLETE.md`
- **FloodAgent Migration:** `MAIN_PY_MAS_MIGRATION.md`
- **FloodDataScheduler Migration:** `FLOOD_SCHEDULER_MAS_MIGRATION.md`
- **Risk Improvements:** `HAZARD_AGENT_RISK_IMPROVEMENTS.md`

---

## Rollback Instructions (If Needed)

If you need to revert the ScoutAgent changes:

```python
# In scout_agent.py __init__:
def __init__(
    self,
    agent_id: str,
    environment: "DynamicGraphEnvironment",
    credentials: Optional["TwitterCredentials"] = None,
    hazard_agent: Optional["HazardAgent"] = None,  # Restore direct reference
    simulation_mode: bool = False,
    simulation_scenario: int = 1,
    use_ml_in_simulation: bool = True
) -> None:
    super().__init__(agent_id, environment)
    self._credentials = credentials
    self.driver = None
    self.hazard_agent = hazard_agent  # Restore attribute

# Restore direct calls in _process_and_forward_tweets:
self.hazard_agent.process_scout_data_with_coordinates(processed_reports)

# Restore direct calls in _process_and_forward_tweets_without_coordinates:
self.hazard_agent.process_scout_data(processed_reports)

# Restore set_hazard_agent method:
def set_hazard_agent(self, hazard_agent) -> None:
    self.hazard_agent = hazard_agent
    logger.info(f"{self.agent_id} linked to {hazard_agent.agent_id}")
```

```python
# In main.py:
scout_agent = ScoutAgent(
    "scout_agent_001",
    environment,
    hazard_agent=hazard_agent,  # Restore direct reference
    simulation_mode=True,
    simulation_scenario=1,
    use_ml_in_simulation=True
)
```

**Note:** This also requires reverting the HazardAgent handler changes.

---

**End of Document**
