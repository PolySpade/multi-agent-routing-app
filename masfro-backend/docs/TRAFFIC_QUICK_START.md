# Google Maps Traffic Integration - Quick Start Guide

**5-Minute Setup Guide**

---

## ✅ What You Get

After this integration, your MAS-FRO system will calculate routes based on:

1. **Flood Risk** (existing) - from FloodAgent + HazardAgent
2. **Real-Time Traffic** (NEW) - from Google Maps
3. **Road Distance** (existing) - from OSMnx

**Example:** A 2km route with moderate flood risk but heavy traffic will be ranked lower than a 2.5km route with low risk and light traffic.

---

## 🚀 Setup (5 Steps)

### Step 1: Get Google Maps API Key (2 minutes)

1. Visit: https://console.cloud.google.com/
2. Create project or select existing
3. Enable "Directions API"
4. Create API Key
5. Copy the key (looks like: `AIzaSyD1234567890abcdefg...`)

**Cost:** FREE for first 40,000 requests/month ($200 credit)

---

### Step 2: Configure Environment (30 seconds)

```bash
cd masfro-backend

# Edit .env file
nano .env  # or use your editor
```

Add this line:
```bash
GOOGLE_MAPS_API_KEY=AIzaSyD1234567890abcdefg...
```

Save and close.

---

### Step 3: Test the Integration (1 minute)

```bash
# Run test script
uv run python scripts/test_traffic_integration.py
```

**Expected output:**
```
✅ Service initialized successfully
✅ Traffic factor: 0.325
🟡 Status: Moderate traffic
✅ All tests passed or skipped
```

If you see errors, check the troubleshooting section below.

---

### Step 4: Add to Main Application (1 minute)

**Edit `app/main.py`:**

Add import at the top:
```python
from app.agents.traffic_agent import TrafficAgent
```

Add initialization in `startup_event()`:
```python
@app.on_event("startup")
async def startup_event():
    # ... existing code ...

    # Initialize TrafficAgent
    try:
        app.state.traffic_agent = TrafficAgent(
            agent_id="traffic_001",
            environment=graph_env,
            update_interval=14400,  # 4 hours
            sample_interval=200     # Sample every 200th edge
        )
        logger.info("✅ TrafficAgent initialized")
    except ValueError:
        logger.warning("⚠️ TrafficAgent disabled (no API key)")
        app.state.traffic_agent = None
```

Add endpoint (optional):
```python
@app.post("/api/admin/update-traffic")
async def update_traffic():
    if not app.state.traffic_agent:
        raise HTTPException(503, "Traffic not enabled")
    return app.state.traffic_agent.update_traffic_data()
```

---

### Step 5: Restart Server (30 seconds)

```bash
# Stop current server (Ctrl+C)
# Start with traffic integration
uvicorn app.main:app --reload
```

**Check logs:**
```
✅ TrafficAgent initialized successfully
Performing initial traffic data update...
Updated 60 edges successfully
```

---

## 🎯 Verify It's Working

### Test 1: Check Status Endpoint

```bash
curl http://localhost:8000/api/traffic/status
```

**Expected:**
```json
{
  "enabled": true,
  "agent_id": "traffic_001",
  "last_update": "2025-11-15T14:30:00",
  "update_interval": 14400
}
```

### Test 2: Calculate Route

```bash
curl -X POST http://localhost:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "start": {"lat": 14.6507, "lon": 121.1029},
    "end": {"lat": 14.6545, "lon": 121.1089}
  }'
```

Route will now consider traffic! Look for `traffic_info` in response.

### Test 3: Manual Update

```bash
curl -X POST http://localhost:8000/api/admin/update-traffic
```

**Expected:**
```json
{
  "success": true,
  "statistics": {
    "edges_updated": 60,
    "avg_traffic_factor": 0.32,
    "elapsed_seconds": 12.4
  }
}
```

---

## 📊 Understanding Traffic Factors

| Traffic Factor | Delay | Meaning | Color |
|----------------|-------|---------|-------|
| 0.0 - 0.2 | 0-20% | Light traffic | 🟢 Green |
| 0.2 - 0.5 | 20-50% | Moderate traffic | 🟡 Yellow |
| 0.5 - 1.0 | 50-100% | Heavy traffic | 🟠 Orange |
| 1.0+ | 100%+ | Severe congestion | 🔴 Red |

**Example:**
- `traffic_factor = 0.5` means the road takes 50% longer than normal
- A normally 10-minute drive now takes 15 minutes

---

## 💰 Cost Management

### Stay Within FREE Tier

**Configuration for FREE (10,800 requests/month):**
```python
TrafficAgent(
    update_interval=14400,  # 4 hours = 6 updates/day
    sample_interval=200     # 60 edges per update
)

# Math: 60 edges × 6 updates × 30 days = 10,800 requests/month
# Cost: $0 (within $200 free credit)
```

**More Frequent Updates ($16/month):**
```python
TrafficAgent(
    update_interval=7200,   # 2 hours = 12 updates/day
    sample_interval=100     # 120 edges per update
)

# Math: 120 × 12 × 30 = 43,200 requests/month
# Cost: $16/month (43,200 × $5/1000 - $200 free = $16)
```

**Monitor usage:** https://console.cloud.google.com/apis/dashboard

---

## 🔧 Troubleshooting

### ❌ "API key not found"

**Problem:** `GOOGLE_MAPS_API_KEY` not in `.env`

**Solution:**
```bash
cd masfro-backend
echo "GOOGLE_MAPS_API_KEY=your_key_here" >> .env
```

---

### ❌ "REQUEST_DENIED"

**Problem:** Directions API not enabled

**Solution:**
1. Go to: https://console.cloud.google.com/apis/library
2. Search "Directions API"
3. Click "Enable"

---

### ❌ "OVER_QUERY_LIMIT"

**Problem:** Exceeded free tier

**Solution:**
- Increase `sample_interval` (e.g., 200 → 500)
- Increase `update_interval` (e.g., 4 hours → 8 hours)
- Enable billing in Google Cloud Console

---

### ⚠️ Traffic data not affecting routes

**Check:**
```python
# In Python console:
from app.environment.graph_manager import DynamicGraphEnvironment
env = DynamicGraphEnvironment()
edge = list(env.graph.edges(keys=True, data=True))[0]
print(edge[-1].get('traffic_factor'))  # Should print a number, not None
```

**If None:**
- TrafficAgent not initialized
- `update_traffic_data()` not called
- Check logs for errors

---

## 📚 Next Steps

1. **Read full documentation:**
   - `docs/GOOGLE_TRAFFIC_INTEGRATION.md` - Complete guide
   - `docs/TRAFFIC_INTEGRATION_EXAMPLE.py` - Code examples

2. **Customize configuration:**
   - Adjust `update_interval` based on needs
   - Tune `sample_interval` for cost/accuracy balance

3. **Monitor costs:**
   - Google Cloud Console → Billing → Cost Table
   - Set budget alerts

4. **Frontend integration:**
   - Display traffic info in route details
   - Show traffic layer on map
   - Add traffic legend

---

## 🎉 Success Criteria

You know it's working when:

✅ Server logs show "TrafficAgent initialized"
✅ `/api/traffic/status` returns `"enabled": true`
✅ Graph edges have `traffic_factor` attribute
✅ Routes change based on time of day
✅ API costs stay within budget

---

## 📞 Support

**Questions?**
- Review: `docs/GOOGLE_TRAFFIC_INTEGRATION.md`
- Test: `scripts/test_traffic_integration.py`
- Check logs: `masfro-backend/logs/masfro.log`

**Google Maps API Help:**
- Documentation: https://developers.google.com/maps/documentation/directions
- Pricing: https://developers.google.com/maps/billing-and-pricing/pricing
- Support: https://developers.google.com/maps/support

---

**Congratulations!** 🎉 Your MAS-FRO system now optimizes routes with real-time traffic data!
